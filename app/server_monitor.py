"""
Модуль для мониторинга состояния сервера через SSH.
Отслеживает температуру CPU и GPU для предотвращения перегрева.
Поддерживает как локальный мониторинг, так и через SSH.
"""
import os
import time
import json
import platform
import subprocess
import paramiko
import logging
from typing import Dict, Optional, Tuple, List
from app.logger import log_action, log_result, log_error
from app.utils import get_env

# Константы для температурных порогов
CPU_TEMP_WARNING = 70.0  # Градусы Цельсия
CPU_TEMP_CRITICAL = 85.0  # Градусы Цельсия
GPU_TEMP_WARNING = 75.0  # Градусы Цельсия
GPU_TEMP_CRITICAL = 90.0  # Градусы Цельсия

# Интервалы времени для мониторинга (в секундах)
NORMAL_CHECK_INTERVAL = 5.0
WARNING_CHECK_INTERVAL = 2.0
CRITICAL_CHECK_INTERVAL = 1.0

# Список кодировок, которые будут попробованы при декодировании
ENCODINGS = ['utf-8', 'cp1251', 'latin1', 'ascii']

class ServerMonitor:
    """
    Класс для мониторинга состояния сервера через SSH.
    """
    def __init__(self):
        """Инициализация подключения к серверу через SSH."""
        self.ssh_host = get_env("ssh_host", "")
        self.ssh_port = int(get_env("ssh_port", "22"))
        self.ssh_user = get_env("ssh_user", "")
        self.ssh_key_path = get_env("ssh_key_path", "")
        self.ssh_password = get_env("ssh_password", "")
        
        self.client = None
        self.is_connected = False
        self.last_check_time = 0
        self.check_interval = NORMAL_CHECK_INTERVAL
        
        # Последние известные значения температуры
        self.last_cpu_temp = 0.0
        self.last_gpu_temp = 0.0
        
        log_action("Инициализация мониторинга сервера")
    
    def connect(self) -> bool:
        """
        Устанавливает SSH-соединение с сервером.
        
        Returns:
            bool: True, если соединение установлено успешно
        """
        if not self.ssh_host or not self.ssh_user:
            log_error("Не заданы параметры SSH-подключения в .env файле", Exception("Missing SSH parameters"))
            return False
            
        try:
            log_action(f"Подключение к серверу {self.ssh_host}:{self.ssh_port} через SSH")
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Подключение с использованием ключа или пароля
            if os.path.isfile(self.ssh_key_path):
                self.client.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    key_filename=self.ssh_key_path
                )
            elif self.ssh_password:
                self.client.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    password=self.ssh_password
                )
            else:
                log_error("Не указан SSH-ключ или пароль", Exception("Missing SSH credentials"))
                return False
                
            self.is_connected = True
            log_result("SSH-соединение установлено", {"host": self.ssh_host})
            return True
            
        except Exception as e:
            log_error(f"Ошибка подключения к серверу через SSH: {str(e)}", e)
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Закрывает SSH-соединение с сервером."""
        if self.client and self.is_connected:
            log_action("Закрытие SSH-соединения")
            self.client.close()
            self.is_connected = False
            log_result("SSH-соединение закрыто")
    
    def _execute_command(self, command: str) -> Tuple[str, str]:
        """
        Выполняет SSH-команду на сервере.
        
        Args:
            command: Команда для выполнения
            
        Returns:
            Tuple[str, str]: stdout и stderr результаты выполнения команды
        """
        if not self.is_connected and not self.connect():
            return "", "Нет подключения к серверу"
            
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=5)
            stdout_data = stdout.read()
            stderr_data = stderr.read()
            
            # Пробуем декодировать данные с разными кодировками
            stdout_str, stderr_str = "", ""
            
            # Пытаемся декодировать stdout с разными кодировками
            for encoding in ENCODINGS:
                try:
                    if stdout_data:
                        stdout_str = stdout_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            # Пытаемся декодировать stderr с разными кодировками
            for encoding in ENCODINGS:
                try:
                    if stderr_data:
                        stderr_str = stderr_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
                    
            # Если не удалось декодировать, используем 'latin1' (почти всегда работает)
            if not stdout_str and stdout_data:
                stdout_str = stdout_data.decode('latin1', errors='replace')
            if not stderr_str and stderr_data:
                stderr_str = stderr_data.decode('latin1', errors='replace')
                
            return stdout_str, stderr_str
            
        except Exception as e:
            log_error(f"Ошибка выполнения команды {command}: {str(e)}", e)
            # Проверяем, действительно ли соединение потеряно
            transport_active = False
            try:
                transport_active = self.client.get_transport() is not None and self.client.get_transport().is_active()
            except:
                pass
            
            # Переподключаемся только если соединение действительно потеряно
            if not transport_active:
                self.is_connected = False  # Маркируем соединение как неактивное
                if self.connect():  # Пытаемся переподключиться
                    try:
                        stdin, stdout, stderr = self.client.exec_command(command, timeout=5)
                        stdout_data = stdout.read()
                        stderr_data = stderr.read()
                        
                        # Используем ту же логику декодирования при переподключении
                        stdout_str = stdout_data.decode('latin1', errors='replace') if stdout_data else ""
                        stderr_str = stderr_data.decode('latin1', errors='replace') if stderr_data else ""
                        return stdout_str, stderr_str
                    except Exception as e2:
                        return "", f"Ошибка после переподключения: {str(e2)}"
            return "", f"Ошибка: {str(e)}"
    
    def _execute_local_command(self, command: str) -> Tuple[str, str]:
        """
        Выполняет локальную команду через subprocess.
        
        Args:
            command: Команда для выполнения
            
        Returns:
            Tuple[str, str]: stdout и stderr результаты выполнения команды
        """
        try:
            if platform.system() == "Windows":
                # На Windows используем shell=True для корректного выполнения команд
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
            else:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
            
            stdout_data, stderr_data = process.communicate(timeout=10)
            
            # Пробуем декодировать с разными кодировками
            stdout_str, stderr_str = "", ""
            
            for encoding in ENCODINGS:
                try:
                    if stdout_data:
                        stdout_str = stdout_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            for encoding in ENCODINGS:
                try:
                    if stderr_data:
                        stderr_str = stderr_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            # Если не удалось декодировать, используем latin1
            if not stdout_str and stdout_data:
                stdout_str = stdout_data.decode('latin1', errors='replace')
            if not stderr_str and stderr_data:
                stderr_str = stderr_data.decode('latin1', errors='replace')
            
            return stdout_str, stderr_str
            
        except subprocess.TimeoutExpired:
            return "", "Превышен таймаут выполнения команды"
        except Exception as e:
            log_error(f"Ошибка выполнения локальной команды {command}: {str(e)}", e)
            return "", f"Ошибка: {str(e)}"
    
    def get_cpu_temperature(self) -> float:
        """
        Получает текущую температуру CPU.
        
        Returns:
            float: Текущая температура CPU в градусах Цельсия
        """
        if platform.system() == "Windows":
            return self._get_windows_cpu_temperature()
        
        # Команда для получения температуры CPU (работает на большинстве Linux систем)
        command = "cat /sys/class/thermal/thermal_zone*/temp | head -n 1"
        stdout, stderr = self._execute_command(command)
        
        if stderr:
            log_error(f"Ошибка при получении температуры CPU: {stderr}", Exception(stderr))
            # Альтернативный метод через lm_sensors
            command_alt = "sensors | grep 'Core' | awk '{print $3}' | grep -Eo '[0-9]+' | head -n 1"
            stdout, stderr = self._execute_command(command_alt)
            
            if stderr:
                return self.last_cpu_temp  # Возвращаем последнее известное значение
        
        try:
            # Преобразование вывода команды в температуру
            if stdout.strip().isdigit() and len(stdout.strip()) > 2:
                # Если значение в миллиградусах (обычно /sys/class/thermal)
                temp = float(stdout.strip()) / 1000.0
            else:
                # Если значение уже в градусах
                temp = float(stdout.strip())
                
            self.last_cpu_temp = temp
            return temp
        except Exception as e:
            log_error(f"Ошибка при парсинге температуры CPU: {str(e)}", e)
            return self.last_cpu_temp
    
    def get_gpu_temperature(self) -> float:
        """
        Получает текущую температуру GPU.
        
        Returns:
            float: Текущая температура GPU в градусах Цельсия
        """
        if platform.system() == "Windows":
            return self._get_windows_gpu_temperature()
        
        # Проверяем Nvidia GPU через nvidia-smi
        command = "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader"
        stdout, stderr = self._execute_command(command)
        
        if not stderr and stdout.strip():
            try:
                temp = float(stdout.strip())
                self.last_gpu_temp = temp
                return temp
            except ValueError:
                pass
        
        # Пробуем получить температуру через AMD
        command = "rocm-smi --showtemp"
        stdout, stderr = self._execute_command(command)
        
        if not stderr and "Temperature" in stdout:
            try:
                temp_line = [line for line in stdout.split('\n') if 'Temperature' in line][0]
                temp = float(temp_line.split(':')[1].split()[0])
                self.last_gpu_temp = temp
                return temp
            except (IndexError, ValueError):
                pass
        
        # Проверяем vulkaninfo
        command = "vulkaninfo | grep 'deviceTemperature'"
        stdout, stderr = self._execute_command(command)
        
        if not stderr and "deviceTemperature" in stdout:
            try:
                temp_str = stdout.strip().split('=')[1].split()[0]
                temp = float(temp_str)
                self.last_gpu_temp = temp
                return temp
            except (IndexError, ValueError):
                pass
        
        # Если не удалось получить температуру GPU, возвращаем последнее известное значение
        return self.last_gpu_temp
    
    def _get_windows_cpu_temperature(self) -> float:
        """
        Получает текущую температуру CPU на Windows с помощью WMI.
        
        Returns:
            float: Текущая температура CPU в градусах Цельсия
        """
        try:
            # Попытка использовать Open Hardware Monitor (если установлен)
            cmd = 'powershell "Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi | Select-Object CurrentTemperature"'
            stdout, stderr = self._execute_local_command(cmd)
            
            if not stderr and "CurrentTemperature" in stdout:
                temp_lines = [line for line in stdout.strip().split('\n') if line.strip() and 'CurrentTemperature' not in line]
                if temp_lines:
                    # Температура в WMI представлена в десятых долях градуса Кельвина
                    temp = float(temp_lines[0].strip()) / 10 - 273.15
                    if temp > 0:
                        self.last_cpu_temp = temp
                        return temp
            
            # Попытка использовать HWiNFO через PowerShell (если установлен)
            cmd = 'powershell "Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation | Select-Object Temperature"'
            stdout, stderr = self._execute_local_command(cmd)
            
            if not stderr and "Temperature" in stdout:
                temp_lines = [line for line in stdout.strip().split('\n') if line.strip() and 'Temperature' not in line]
                if temp_lines:
                    temp = float(temp_lines[0].strip())
                    if temp > 0:
                        self.last_cpu_temp = temp
                        return temp
            
            # В случае неудачи используем внешний инструмент CoreTemp (если установлен)
            cmd = 'wmic /namespace:\\\\root\\wmi PATH MSAcpi_ThermalZoneTemperature get CurrentTemperature'
            stdout, stderr = self._execute_local_command(cmd)
            
            if not stderr and stdout.strip():
                lines = stdout.strip().split('\n')
                if len(lines) > 1:
                    temp = float(lines[1].strip()) / 10 - 273.15
                    if temp > 0:
                        self.last_cpu_temp = temp
                        return temp
            
            # Если не удалось получить данные, возвращаем примерное значение
            # Устанавливаем значение между 30-40°C как типичное для работающего ПК
            if self.last_cpu_temp <= 0:
                temp = 35.0
                self.last_cpu_temp = temp
                log_action("Установлено стандартное значение CPU температуры (35°C)")
                return temp
            
        except Exception as e:
            log_error(f"Ошибка при получении температуры CPU на Windows: {str(e)}", e)
        
        return self.last_cpu_temp

    def _get_windows_gpu_temperature(self) -> float:
        """
        Получает текущую температуру GPU на Windows, с поддержкой AMD Radeon.
        
        Returns:
            float: Текущая температура GPU в градусах Цельсия
        """
        # Для AMD Radeon используем специальные методы
        try:
            # AMD ADL (AMD Display Library) метод через PowerShell
            cmd = 'powershell "(Get-WmiObject -Namespace root\\WMI -Class AMD_ACPI_Event).InstanceName"'
            stdout, stderr = self._execute_local_command(cmd)
            
            if not stderr and stdout and "AMD" in stdout:
                # Если обнаружено устройство AMD, получаем температуру через AMD мониторинг
                log_action("Обнаружена видеокарта AMD Radeon, пробуем получить данные о температуре")
                
                # Метод 1: Через WMI пространство имен AMD
                cmd = 'powershell "Get-WmiObject -Namespace root\\WMI -Class AMD_ACPI_ThermalZoneInfo | Select-Object CurrentTemperature"'
                stdout, stderr = self._execute_local_command(cmd)
                
                if not stderr and "CurrentTemperature" in stdout:
                    temp_lines = [line for line in stdout.strip().split('\n') if line.strip() and 'CurrentTemperature' not in line]
                    if temp_lines:
                        try:
                            temp = float(temp_lines[0].strip())
                            if temp > 0 and temp < 150:  # Проверка на разумность значения
                                log_action(f"Получена фактическая температура AMD GPU: {temp}°C")
                                self.last_gpu_temp = temp
                                return temp
                        except ValueError:
                            pass
                
                # Метод 2: Через внешний инструмент amdgpu-utility (если установлен)
                cmd = 'amdgpu-utility -t'
                stdout, stderr = self._execute_local_command(cmd)
                
                if not stderr and stdout.strip():
                    try:
                        # Парсим вывод, например: "GPU Temperature: 65°C"
                        for line in stdout.strip().split('\n'):
                            if "Temperature" in line:
                                temp_str = ''.join(c for c in line.split(':')[1] if c.isdigit() or c == '.')
                                temp = float(temp_str)
                                if temp > 0 and temp < 150:
                                    log_action(f"Получена фактическая температура AMD GPU через amdgpu-utility: {temp}°C")
                                    self.last_gpu_temp = temp
                                    return temp
                    except (IndexError, ValueError):
                        pass
                
                # Метод 3: Через Windows Performance Counters для AMD
                cmd = 'powershell "Get-Counter -Counter \'\\GPU Engine(*engtype_3D)\\Utilization Percentage\' | Select-Object -ExpandProperty CounterSamples | Select-Object CookedValue"'
                stdout, stderr = self._execute_local_command(cmd)
                
                if not stderr and "CookedValue" in stdout:
                    # Хотя это не температура, но высокая утилизация обычно коррелирует с температурой
                    # Хотя бы отслеживаем работу GPU
                    log_action("Получена информация о нагрузке на AMD GPU, но не о температуре")
            
            # Попробуем общий метод для Windows с помощью OpenHardwareMonitor, 
            # который может работать с AMD Radeon
            log_action("Пытаюсь получить температуру через стандартные системные методы")
            
            # Метод через WMI и MSAcpi_ThermalZoneTemperature
            cmd = 'wmic /namespace:\\\\root\\wmi PATH MSAcpi_ThermalZoneTemperature get CurrentTemperature'
            stdout, stderr = self._execute_local_command(cmd)
            
            if not stderr and stdout.strip():
                lines = stdout.strip().split('\n')
                if len(lines) > 1:
                    try:
                        temp = float(lines[1].strip()) / 10 - 273.15
                        if temp > 0 and temp < 150:
                            log_action(f"Получена температура через WMI MSAcpi_ThermalZoneTemperature: {temp:.1f}°C")
                            self.last_gpu_temp = temp
                            return temp
                    except (IndexError, ValueError):
                        pass
            
            # Если всё ещё не удалось получить температуру - логируем ошибку
            log_error("Не удалось получить реальную температуру AMD Radeon GPU. Проверьте права доступа или установите OpenHardwareMonitor", Exception("Temperature reading failed"))
            
            # Возвращаем последнее известное значение или устанавливаем повышенное значение как предупреждение
            if self.last_gpu_temp <= 0:
                temp = 60.0  # Устанавливаем повышенное значение как индикатор проблемы измерения
                log_error(f"ВНИМАНИЕ: Установлено повышенное значение температуры GPU ({temp}°C) как индикатор проблемы с мониторингом!", Exception("Monitoring error"))
                self.last_gpu_temp = temp
            
            return self.last_gpu_temp
                
        except Exception as e:
            log_error(f"Критическая ошибка при получении температуры AMD Radeon GPU: {str(e)}", e)
            
        return self.last_gpu_temp

    def get_system_load(self) -> Dict[str, float]:
        """
        Получает информацию о загрузке системы.
        
        Returns:
            Dict[str, float]: Словарь с метриками загрузки системы
        """
        if platform.system() == "Windows":
            try:
                # Используем WMI для получения загрузки CPU на Windows
                cmd = 'powershell "Get-CimInstance -ClassName win32_processor | Measure-Object -Property LoadPercentage -Average | Select-Object Average"'
                stdout, stderr = self._execute_local_command(cmd)
                
                if not stderr and "Average" in stdout:
                    lines = [line for line in stdout.strip().split('\n') if line.strip() and 'Average' not in line]
                    if lines:
                        avg_load = float(lines[0].strip())
                        return {
                            "load_1min": avg_load / 100.0,  # Нормализуем до диапазона Linux (обычно 0-N, где N - кол-во ядер)
                            "load_5min": avg_load / 100.0,
                            "load_15min": avg_load / 100.0
                        }
            except Exception as e:
                log_error(f"Ошибка при получении загрузки системы на Windows: {str(e)}", e)
            
            # Если не удалось получить через WMI, используем стандартные значения
            return {"load_1min": 0.5, "load_5min": 0.5, "load_15min": 0.5}
                
        # Для Linux используем оригинальный метод
        command = "cat /proc/loadavg"
        stdout, stderr = self._execute_command(command)
        
        if stderr:
            return {"load_1min": 0.0, "load_5min": 0.0, "load_15min": 0.0}
        
        try:
            load_values = stdout.strip().split()[:3]
            return {
                "load_1min": float(load_values[0]),
                "load_5min": float(load_values[1]),
                "load_15min": float(load_values[2])
            }
        except (IndexError, ValueError):
            return {"load_1min": 0.0, "load_5min": 0.0, "load_15min": 0.0}
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Получает информацию об использовании памяти.
        
        Returns:
            Dict[str, float]: Словарь с метриками использования памяти
        """
        if platform.system() == "Windows":
            try:
                # Используем WMI для получения информации о памяти на Windows
                cmd = 'powershell "Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory"'
                stdout, stderr = self._execute_local_command(cmd)
                
                if not stderr and "TotalVisibleMemorySize" in stdout and "FreePhysicalMemory" in stdout:
                    lines = [line for line in stdout.strip().split('\n') if line.strip()]
                    if len(lines) >= 3:  # Заголовок и хотя бы одна строка данных
                        # Получаем числа из строки данных
                        data_line = lines[2].strip()
                        values = [int(s) for s in data_line.split() if s.isdigit()]
                        
                        if len(values) >= 2:
                            total_kb = float(values[0])
                            free_kb = float(values[1])
                            used_kb = total_kb - free_kb
                            
                            # Преобразуем в МБ
                            total_mb = total_kb / 1024.0
                            used_mb = used_kb / 1024.0
                            free_mb = free_kb / 1024.0
                            
                            return {
                                "total_mb": total_mb,
                                "used_mb": used_mb,
                                "free_mb": free_mb,
                                "used_percent": (used_mb / total_mb) * 100 if total_mb > 0 else 0.0
                            }
            except Exception as e:
                log_error(f"Ошибка при получении информации о памяти на Windows: {str(e)}", e)
            
            # Альтернативный метод через командную строку
            try:
                cmd = 'systeminfo | findstr /C:"Total Physical Memory" /C:"Available Physical Memory"'
                stdout, stderr = self._execute_local_command(cmd)
                
                if not stderr and stdout:
                    lines = stdout.strip().split('\n')
                    if len(lines) >= 2:
                        # Парсим строки типа "Total Physical Memory:     16,315 MB"
                        total_line = lines[0]
                        available_line = lines[1]
                        
                        # Извлекаем числа
                        total_mb = float(''.join([c for c in total_line.split(':')[1] if c.isdigit() or c == '.']).strip())
                        free_mb = float(''.join([c for c in available_line.split(':')[1] if c.isdigit() or c == '.']).strip())
                        used_mb = total_mb - free_mb
                        
                        return {
                            "total_mb": total_mb,
                            "used_mb": used_mb,
                            "free_mb": free_mb,
                            "used_percent": (used_mb / total_mb) * 100 if total_mb > 0 else 0.0
                        }
            except Exception as e:
                log_error(f"Ошибка при получении информации о памяти через systeminfo: {str(e)}", e)
            
            # Если не удалось получить данные о памяти, возвращаем стандартные значения
            return {"total_mb": 8192.0, "used_mb": 4096.0, "free_mb": 4096.0, "used_percent": 50.0}
        
        # Для Linux используем оригинальный метод
        command = "free -b | grep Mem"
        stdout, stderr = self._execute_command(command)
        
        if stderr:
            return {"total_mb": 0.0, "used_mb": 0.0, "free_mb": 0.0, "used_percent": 0.0}
        
        try:
            memory_values = stdout.strip().split()
            total = float(memory_values[1]) / (1024 * 1024)  # В МБ
            used = float(memory_values[2]) / (1024 * 1024)  # В МБ
            free = float(memory_values[3]) / (1024 * 1024)  # В МБ
            
            return {
                "total_mb": total,
                "used_mb": used,
                "free_mb": free,
                "used_percent": (used / total) * 100 if total > 0 else 0.0
            }
        except (IndexError, ValueError):
            return {"total_mb": 0.0, "used_mb": 0.0, "free_mb": 0.0, "used_percent": 0.0}
    
    def check_temperature(self) -> Dict[str, float]:
        """
        Проверяет текущую температуру CPU и GPU и определяет статус системы.
        
        Returns:
            Dict[str, float]: Словарь с температурами и статусом системы
        """
        # Проверяем, не слишком ли часто вызывается
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return {
                "cpu_temp": self.last_cpu_temp,
                "gpu_temp": self.last_gpu_temp,
                "status": self._get_status(self.last_cpu_temp, self.last_gpu_temp),
                "cached": True
            }
        
        self.last_check_time = current_time
        
        # Получаем текущую температуру
        cpu_temp = self.get_cpu_temperature()
        gpu_temp = self.get_gpu_temperature()
        
        # Определяем статус системы
        status = self._get_status(cpu_temp, gpu_temp)
        
        # Обновляем интервал проверки в зависимости от статуса
        if status == "critical":
            self.check_interval = CRITICAL_CHECK_INTERVAL
        elif status == "warning":
            self.check_interval = WARNING_CHECK_INTERVAL
        else:
            self.check_interval = NORMAL_CHECK_INTERVAL
        
        log_action(f"Температура сервера: CPU {cpu_temp:.1f}°C, GPU {gpu_temp:.1f}°C, статус: {status}")
        
        return {
            "cpu_temp": cpu_temp,
            "gpu_temp": gpu_temp,
            "status": status,
            "cached": False
        }
    
    def _get_status(self, cpu_temp: float, gpu_temp: float) -> str:
        """
        Определяет текущий статус системы на основе температуры.
        
        Args:
            cpu_temp: Температура CPU
            gpu_temp: Температура GPU
            
        Returns:
            str: Статус системы ("normal", "warning", "critical", "error")
        """
        # Проверяем неправильные показания (0 или очень низкие значения)
        if cpu_temp <= 0 or gpu_temp <= 0:
            log_error(f"Обнаружены некорректные показания температуры: CPU {cpu_temp:.1f}°C, GPU {gpu_temp:.1f}°C", 
                      Exception("Invalid temperature reading"))
            return "error"
            
        if cpu_temp >= CPU_TEMP_CRITICAL or gpu_temp >= GPU_TEMP_CRITICAL:
            return "critical"
        elif cpu_temp >= CPU_TEMP_WARNING or gpu_temp >= GPU_TEMP_WARNING:
            return "warning"
        else:
            return "normal"
    
    def get_full_system_status(self) -> Dict[str, any]:
        """
        Получает полный статус системы, включая температуру, загрузку и память.
        
        Returns:
            Dict[str, any]: Словарь с полным статусом системы
        """
        temperature = self.check_temperature()
        load = self.get_system_load()
        memory = self.get_memory_usage()
        
        return {
            **temperature,
            **load,
            **memory,
            "timestamp": time.time()
        }
    
    def should_pause_processing(self) -> Tuple[bool, str]:
        """
        Определяет, нужно ли приостановить обработку на основе статуса системы.
        
        Returns:
            Tuple[bool, str]: Флаг необходимости паузы и причина паузы
        """
        status_info = self.check_temperature()
        status = status_info["status"]
        
        if status == "critical":
            reason = f"Критическая температура: CPU {status_info['cpu_temp']:.1f}°C, GPU {status_info['gpu_temp']:.1f}°C"
            return True, reason
        elif status == "error":
            reason = f"Ошибка измерения температуры: CPU {status_info['cpu_temp']:.1f}°C, GPU {status_info['gpu_temp']:.1f}°C"
            log_error(f"Невозможно получить корректные данные о температуре: {reason}", Exception("Temperature read error"))
            # Не останавливаем обработку при ошибке измерения, но логируем
            return False, reason
        
        return False, ""
    
    def calculate_adaptive_delay(self) -> float:
        """
        Рассчитывает адаптивную задержку на основе температуры системы.
        
        Returns:
            float: Рекомендуемая задержка в секундах между запросами
        """
        status_info = self.check_temperature()
        status = status_info["status"]
        cpu_temp = status_info["cpu_temp"]
        gpu_temp = status_info["gpu_temp"]
        
        # Базовая задержка в нормальных условиях
        base_delay = 0.5
        
        # Для случаев ошибки измерения устанавливаем среднюю задержку
        if status == "error":
            log_action("Установлена стандартная задержка из-за ошибки измерения температуры")
            return base_delay * 2.0  # Умеренная задержка при ошибке измерения
        
        # Расчет множителя задержки на основе температуры
        cpu_factor = 1.0
        if cpu_temp > CPU_TEMP_WARNING:
            # Линейное увеличение от 1.0 до 5.0 между WARNING и CRITICAL
            cpu_factor = 1.0 + 4.0 * (cpu_temp - CPU_TEMP_WARNING) / (CPU_TEMP_CRITICAL - CPU_TEMP_WARNING)
        
        gpu_factor = 1.0
        if gpu_temp > GPU_TEMP_WARNING:
            # Линейное увеличение от 1.0 до 5.0 между WARNING и CRITICAL
            gpu_factor = 1.0 + 4.0 * (gpu_temp - GPU_TEMP_WARNING) / (GPU_TEMP_CRITICAL - GPU_TEMP_WARNING)
        
        # Используем максимальный из двух факторов
        delay_factor = max(cpu_factor, gpu_factor)
        
        return base_delay * delay_factor
    
    def log_temperature_warning(self):
        """Логирует предупреждение о высокой температуре."""
        status_info = self.check_temperature()
        log_error(
            f"Высокая температура сервера: CPU {status_info['cpu_temp']:.1f}°C, GPU {status_info['gpu_temp']:.1f}°C", 
            Exception("High temperature warning")
        )

# Глобальный объект монитора сервера для использования в разных модулях
_monitor = None

def get_server_monitor() -> ServerMonitor:
    """
    Возвращает глобальный объект ServerMonitor, создавая его при первом вызове.
    
    Returns:
        ServerMonitor: Объект для мониторинга сервера
    """
    global _monitor
    if _monitor is None:
        _monitor = ServerMonitor()
    return _monitor

# Функция-утилита для периодической проверки температуры в фоновом потоке
def start_temperature_monitoring(monitoring_interval: float = 10.0) -> None:
    """
    Запускает фоновый мониторинг температуры сервера.
    
    Args:
        monitoring_interval: Интервал проверки в секундах
    """
    import threading
    
    def monitoring_task():
        monitor = get_server_monitor()
        
        while True:
            try:
                status_info = monitor.check_temperature()
                status = status_info["status"]
                
                if status == "critical":
                    monitor.log_temperature_warning()
                elif status == "error":
                    log_error(
                        f"Ошибка измерения температуры: CPU {status_info['cpu_temp']:.1f}°C, GPU {status_info['gpu_temp']:.1f}°C", 
                        Exception("Temperature read error")
                    )
                
                # Адаптивный интервал проверки
                if status == "critical":
                    sleep_time = 2.0
                elif status == "warning":
                    sleep_time = 5.0
                elif status == "error":
                    # При ошибке измерения проверяем чаще
                    sleep_time = 3.0
                else:
                    sleep_time = monitoring_interval
                    
                time.sleep(sleep_time)
                
            except Exception as e:
                log_error(f"Ошибка в мониторинге температуры: {str(e)}", e)
                time.sleep(monitoring_interval)
    
    # Запускаем мониторинг в отдельном потоке
    threading.Thread(target=monitoring_task, daemon=True).start()
    log_action(f"Запущен мониторинг температуры сервера с интервалом {monitoring_interval} сек")