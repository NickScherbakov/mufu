"""
Тестирование возможностей рассуждения (reasoning) API llama.cpp.
Этот скрипт проверяет способности к структурированному мышлению и рассуждению
модели Reka-Flash-3-21B-Reasoning через API llama.cpp.
"""
import os
import sys

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
import time
from datetime import datetime
from pathlib import Path
from app.utils import get_env
from app.logger import setup_logging, log_action, log_result, log_error
from app.server_monitor import get_server_monitor, start_temperature_monitoring
from app.optimized_prompts import MERGE_SORT_PROMPT, LOGICAL_PUZZLE_PROMPT, WEATHER_FUNCTION_PROMPT

# Константы для тестов
DEFAULT_TIMEOUT = 180  # 3 минуты для обработки больших запросов (уменьшено с 5 минут)
REASONING_TEMPERATURE = 0.1  # Низкая температура для логических рассуждений
REASONING_TOP_P = 0.9  # Оптимальный параметр для рассуждений
MAX_TOKENS = 2048  # Максимальное количество токенов для рассуждений (уменьшено с 4096)

# Константы для контроля температуры
PAUSE_BETWEEN_TESTS = 30.0  # Пауза между тестами в секундах
PAUSE_DURING_CRITICAL = 120.0  # Длительная пауза при критической температуре
ADAPTIVE_CHUNK_PROCESSING = True  # Включить адаптивную обработку чанков
MAX_CHUNKS_TO_PROCESS = 2500  # Максимальное количество чанков для обработки

def test_direct_reasoning(api_url, api_key=None):
    """
    Проверяет способность модели к прямым рассуждениям через API llama.cpp.
    Использует оптимизированный промпт для предотвращения зацикливания.
    
    Args:
        api_url: URL базового API (например, http://192.168.2.74:3131/v1)
        api_key: Ключ API, если требуется
        
    Returns:
        dict: Результаты теста с оценкой качества
    """
    log_action("Тестирование прямых рассуждений через llama.cpp API с оптимизированным промптом")
    
    # Проверка температуры перед запросом
    server_monitor = get_server_monitor()
    should_pause, reason = server_monitor.should_pause_processing()
    
    if should_pause:
        log_error(f"Тест отложен: {reason}", Exception("Temperature critical"))
        log_action(f"Ожидание {PAUSE_DURING_CRITICAL} секунд для снижения температуры")
        time.sleep(PAUSE_DURING_CRITICAL)
        
        # Повторная проверка после паузы
        should_pause, reason = server_monitor.should_pause_processing()
        if should_pause:
            log_error("Температура остается критической после паузы, тест пропущен", Exception("Temperature critical"))
            return {"success": False, "error": f"Тест пропущен из-за критической температуры: {reason}"}
    
    # Формируем заголовки
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "NA":
        headers["Authorization"] = f"Bearer {api_key}"
    
    # Используем оптимизированный промпт для логической задачи
    payload = LOGICAL_PUZZLE_PROMPT.copy()
    
    log_action(f"Отправка запроса на рассуждение к {api_url}/chat/completions")
    
    try:
        # Отправляем запрос
        start_time = time.time()
        response = requests.post(
            f"{api_url.rstrip('/')}/chat/completions", 
            json=payload, 
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )
        response_time = time.time() - start_time
        
        response.raise_for_status()
        result = response.json()
        
        # Проверяем формат ответа
        if "choices" in result and len(result["choices"]) > 0:
            answer = result["choices"][0]["message"].get("content", "")
            
            # ВЫВОД ПОЛНОГО ОТВЕТА МОДЕЛИ В КОНСОЛЬ
            print("\n" + "=" * 80)
            print("ОТВЕТ API LLAMA.CPP (ПРЯМОЕ РАССУЖДЕНИЕ):")
            print("=" * 80)
            print(answer)
            print("=" * 80 + "\n")
            
            # Логируем полный ответ для последующего анализа
            log_action("Получен ответ от API Llama.cpp")
            log_result("ПОЛНЫЙ ТЕКСТ ОТВЕТА API", {"ответ": answer})
            
            # Анализируем качество рассуждения
            steps_quality = analyze_reasoning_steps(answer)
            
            # Логирование текущей температуры после запроса
            temp_status = server_monitor.check_temperature()
            log_result("Получен ответ с рассуждением", {
                "время_ответа": f"{response_time:.2f} сек",
                "оценка_качества": steps_quality["score"],
                "комментарий": steps_quality["comment"],
                "температура_cpu": f"{temp_status['cpu_temp']:.1f}°C",
                "температура_gpu": f"{temp_status['gpu_temp']:.1f}°C"
            })
            
            return {
                "success": True,
                "answer": answer,
                "response_time": response_time,
                "quality": steps_quality,
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "temperature": temp_status
            }
        else:
            log_error("Некорректный формат ответа", Exception("Отсутствует поле choices"))
            return {"success": False, "error": "Некорректный формат ответа"}
            
    except requests.exceptions.Timeout:
        log_error("Таймаут при ожидании ответа", Exception("Timeout"))
        return {"success": False, "error": "Таймаут при ожидании ответа"}
    except Exception as e:
        log_error(f"Ошибка при отправке запроса: {str(e)}", e)
        return {"success": False, "error": str(e)}

def test_function_calling(api_url, api_key=None):
    """
    Тестирует возможности вызова функций (function calling) через API.
    Использует оптимизированный промпт для функциональных вызовов.
    
    Args:
        api_url: URL базового API (например, http://192.168.2.74:3131/v1)
        api_key: Ключ API, если требуется
        
    Returns:
        dict: Результаты теста function calling
    """
    log_action("Тестирование функциональных вызовов через llama.cpp API с оптимизированным промптом")
    
    # Проверка температуры перед запросом
    server_monitor = get_server_monitor()
    should_pause, reason = server_monitor.should_pause_processing()
    
    if should_pause:
        log_error(f"Тест отложен: {reason}", Exception("Temperature critical"))
        log_action(f"Ожидание {PAUSE_DURING_CRITICAL} секунд для снижения температуры")
        time.sleep(PAUSE_DURING_CRITICAL)
        
        # Повторная проверка после паузы
        should_pause, reason = server_monitor.should_pause_processing()
        if should_pause:
            log_error("Температура остается критической после паузы, тест пропущен", Exception("Temperature critical"))
            return {"success": False, "error": f"Тест пропущен из-за критической температуры: {reason}"}
    
    # Формируем заголовки
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "NA":
        headers["Authorization"] = f"Bearer {api_key}"
    
    # Используем оптимизированный промпт для функционального вызова
    payload = WEATHER_FUNCTION_PROMPT.copy()
    
    log_action(f"Отправка запроса function calling к {api_url}/chat/completions")
    
    try:
        # Отправляем запрос
        start_time = time.time()
        response = requests.post(
            f"{api_url.rstrip('/')}/chat/completions", 
            json=payload, 
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )
        response_time = time.time() - start_time
        
        response.raise_for_status()
        result = response.json()
        
        # Проверяем наличие функционального вызова
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0]["message"]
            
            # ВЫВОД ПОЛНОГО ОТВЕТА МОДЕЛИ В КОНСОЛЬ (независимо от наличия function_call)
            print("\n" + "=" * 80)
            print("ОТВЕТ API LLAMA.CPP (ФУНКЦИОНАЛЬНЫЙ ВЫЗОВ):")
            print("=" * 80)
            
            if "function_call" in message:
                function_call = message["function_call"]
                print(f"Имя функции: {function_call.get('name', '')}")
                print(f"Аргументы: {function_call.get('arguments', '')}")
            else:
                print(f"Ответ без функционального вызова: {message.get('content', '')}")
                
            print("=" * 80 + "\n")
            
            # Логируем полный ответ для последующего анализа
            if "function_call" in message:
                function_call = message["function_call"]
                log_action("Получен функциональный вызов от API Llama.cpp")
                log_result("ПОЛНЫЙ ТЕКСТ ФУНКЦИОНАЛЬНОГО ВЫЗОВА", {
                    "функция": function_call.get("name", ""),
                    "аргументы": function_call.get("arguments", "")
                })
                
                # Логирование текущей температуры после запроса
                temp_status = server_monitor.check_temperature()
                
                # Анализируем качество функционального вызова
                function_quality = analyze_function_call(function_call)
                
                return {
                    "success": True,
                    "function_call": function_call,
                    "quality": function_quality,
                    "response_time": response_time,
                    "temperature": temp_status
                }
            else:
                content = message.get("content", "")
                log_error("Функциональный вызов не выполнен", Exception("Нет поля function_call в ответе"))
                log_result("ПОЛНЫЙ ТЕКСТ ОТВЕТА БЕЗ ФУНКЦИОНАЛЬНОГО ВЫЗОВА", {"ответ": content})
                
                return {
                    "success": False, 
                    "error": "Модель не выполнила функциональный вызов",
                    "response": content
                }
        else:
            log_error("Некорректный формат ответа", Exception("Отсутствует поле choices"))
            return {"success": False, "error": "Некорректный формат ответа"}
            
    except requests.exceptions.Timeout:
        log_error("Таймаут при ожидании ответа", Exception("Timeout"))
        return {"success": False, "error": "Таймаут при ожидании ответа"}
    except Exception as e:
        log_error(f"Ошибка при отправке запроса: {str(e)}", e)
        return {"success": False, "error": str(e)}

def test_stream_reasoning(api_url, api_key=None):
    """
    Тестирует потоковую передачу рассуждений от модели.
    Использует оптимизированный промпт для алгоритма сортировки слиянием.
    
    Args:
        api_url: URL базового API
        api_key: Ключ API, если требуется
        
    Returns:
        dict: Результаты теста потоковой передачи
    """
    log_action("Тестирование потоковой передачи рассуждений с оптимизированным промптом")
    
    # Проверка температуры перед запросом
    server_monitor = get_server_monitor()
    should_pause, reason = server_monitor.should_pause_processing()
    
    if should_pause:
        log_error(f"Тест отложен: {reason}", Exception("Temperature critical"))
        log_action(f"Ожидание {PAUSE_DURING_CRITICAL} секунд для снижения температуры")
        time.sleep(PAUSE_DURING_CRITICAL)
        
        # Повторная проверка после паузы
        should_pause, reason = server_monitor.should_pause_processing()
        if should_pause:
            log_error("Температура остается критической после паузы, тест пропущен", Exception("Temperature critical"))
            return {"success": False, "error": f"Тест пропущен из-за критической температуры: {reason}"}
    
    # Формируем заголовки
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "NA":
        headers["Authorization"] = f"Bearer {api_key}"
    
    # Используем оптимизированный промпт для задачи алгоритма сортировки слиянием
    payload = MERGE_SORT_PROMPT.copy()
    # Включаем потоковый режим
    payload["stream"] = True
    
    log_action(f"Отправка запроса на потоковое рассуждение к {api_url}/chat/completions")
    
    try:
        # Засекаем время начала
        start_time = time.time()
        
        # Отправляем запрос с потоковой передачей
        response = requests.post(
            f"{api_url.rstrip('/')}/chat/completions", 
            json=payload, 
            headers=headers,
            stream=True,
            timeout=DEFAULT_TIMEOUT
        )
        
        response.raise_for_status()
        
        # Переменные для сбора данных
        accumulated_text = ""
        chunk_count = 0
        first_chunk_time = None
        last_temperature_check = time.time()
        temperature_check_interval = 15.0  # Увеличиваем интервал до 15 секунд
        
        # Выводим заголовок для начала потокового ответа
        print("\n" + "=" * 80)
        print("ОТВЕТ API LLAMA.CPP (ПОТОКОВАЯ ПЕРЕДАЧА):")
        print("=" * 80)
        
        # Обрабатываем потоковую передачу
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: ') and line_text != 'data: [DONE]':
                    chunk_count += 1
                    
                    # Запоминаем время получения первого чанка
                    if chunk_count == 1:
                        first_chunk_time = time.time()
                    
                    try:
                        data = json.loads(line_text[6:])
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                content = delta["content"]
                                accumulated_text += content
                                
                                # Выводим содержимое чанка сразу в консоль
                                print(content, end='', flush=True)
                                
                                # Логируем каждые 50 чанков с указанием текущего состояния
                                if chunk_count % 50 == 0:
                                    log_action(f"Получено {chunk_count} чанков данных")
                                
                                # Периодическая проверка температуры
                                current_time = time.time()
                                if current_time - last_temperature_check >= temperature_check_interval:
                                    last_temperature_check = current_time
                                    # Используем cached значения температуры, если возможно
                                    temp_info = server_monitor.check_temperature()
                                    
                                    # Логируем только если температура не в норме
                                    if temp_info["status"] != "normal":
                                        log_action(f"Текущая температура после {chunk_count} чанков: CPU {temp_info['cpu_temp']:.1f}°C, GPU {temp_info['gpu_temp']:.1f}°C, статус: {temp_info['status']}")
                                    
                                    # Адаптивная задержка в зависимости от температуры
                                    if ADAPTIVE_CHUNK_PROCESSING and temp_info["status"] != "normal":
                                        delay = server_monitor.calculate_adaptive_delay()
                                        if delay > 0.1:  # Если задержка существенная
                                            log_action(f"Адаптивная задержка {delay:.2f}с для снижения нагрузки")
                                            time.sleep(delay)
                                
                                # Ограничение на количество обрабатываемых чанков
                                if chunk_count >= MAX_CHUNKS_TO_PROCESS:
                                    log_action(f"Достигнут лимит в {MAX_CHUNKS_TO_PROCESS} чанков, обработка прервана")
                                    break
                                    
                    except json.JSONDecodeError:
                        continue
        
        # Завершаем вывод потокового ответа в консоль
        print("\n" + "=" * 80 + "\n")
        
        # Рассчитываем метрики
        total_time = time.time() - start_time
        time_to_first_chunk = first_chunk_time - start_time if first_chunk_time else None
        
        # Проверяем температуру после завершения
        final_temp = server_monitor.check_temperature()
        
        # Логируем полный текст ответа в лог-файл
        log_result("ПОЛНЫЙ ТЕКСТ ПОТОКОВОГО ОТВЕТА API", {"ответ": accumulated_text})
        
        log_result("Завершена потоковая передача рассуждения", {
            "общее_время": f"{total_time:.2f} сек",
            "время_до_первого_чанка": f"{time_to_first_chunk:.2f} сек" if time_to_first_chunk else "N/A",
            "количество_чанков": chunk_count,
            "длина_текста": len(accumulated_text),
            "температура_cpu": f"{final_temp['cpu_temp']:.1f}°C",
            "температура_gpu": f"{final_temp['gpu_temp']:.1f}°C"
        })
        
        # Оценка структуры потокового ответа
        streaming_quality = analyze_streaming_quality(accumulated_text)
        
        return {
            "success": True,
            "total_time": total_time,
            "time_to_first_chunk": time_to_first_chunk,
            "chunk_count": chunk_count, 
            "text_length": len(accumulated_text),
            "quality": streaming_quality,
            "answer": accumulated_text,  # Полный ответ теперь сохраняется
            "answer_sample": accumulated_text[:300] + "..." if len(accumulated_text) > 300 else accumulated_text,
            "temperature": final_temp
        }
        
    except requests.exceptions.Timeout:
        log_error("Таймаут при потоковой передаче", Exception("Timeout"))
        return {"success": False, "error": "Таймаут при потоковой передаче"}
    except Exception as e:
        log_error(f"Ошибка при потоковой передаче: {str(e)}", e)
        return {"success": False, "error": str(e)}

def analyze_reasoning_steps(text):
    """
    Анализирует качество рассуждений в ответе.
    
    Args:
        text: Текст ответа
        
    Returns:
        dict: Оценка качества рассуждений
    """
    score = 0
    comments = []
    
    # Проверяем наличие структурированных секций из оптимизированного формата
    if "АНАЛИЗ УСЛОВИЙ:" in text:
        score += 1
        comments.append("Присутствует раздел анализа условий")
    
    if "РАССУЖДЕНИЕ:" in text:
        score += 1
        comments.append("Присутствует раздел с рассуждением")
    
    if "ОТВЕТ:" in text:
        score += 1
        comments.append("Присутствует четкий финальный ответ")
    
    # Проверяем наличие шагов рассуждения
    if "шаг" in text.lower() or "step" in text.lower():
        score += 1
        comments.append("Присутствуют явные шаги рассуждения")
    
    # Проверяем наличие логических выводов
    if "следовательно" in text.lower() or "значит" in text.lower() or "therefore" in text.lower():
        score += 1
        comments.append("Присутствуют логические выводы")
    
    # Проверяем структуру рассуждения
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        score += 1
        comments.append("Хорошая структура с несколькими параграфами")
    
    # Проверяем наличие конкретного решения для задачи
    if "у ани" in text.lower() and "у бори" in text.lower() and "у вовы" in text.lower():
        score += 1
        comments.append("Содержит решение для всех персонажей задачи")
        
    # Проверяем наличие цветов в решении
    colors = ["красный", "синий", "зеленый"]
    if all(color in text.lower() for color in colors):
        score += 1
        comments.append("Упоминаются все цвета из задачи")
    
    # Общая оценка
    comment = "Отлично" if score >= 5 else "Хорошо" if score >= 3 else "Удовлетворительно"
    
    return {
        "score": score,
        "max_score": 8,  # Увеличено, так как добавили критерии для структурированного формата
        "comment": comment,
        "details": comments
    }

def analyze_function_call(function_call):
    """
    Анализирует качество функционального вызова.
    
    Args:
        function_call: Словарь с данными функционального вызова
        
    Returns:
        dict: Оценка качества функционального вызова
    """
    score = 0
    comments = []
    
    # Проверяем правильность имени функции
    if function_call.get("name") == "get_weather":
        score += 1
        comments.append("Корректное имя функции")
    
    # Анализируем аргументы
    try:
        args = json.loads(function_call.get("arguments", "{}"))
        
        # Проверяем наличие обязательного аргумента city
        if "city" in args:
            score += 1
            comments.append("Присутствует обязательный аргумент 'city'")
            
            # Проверяем значение city
            if args["city"].lower() == "москва" or args["city"].lower() == "moscow":
                score += 1
                comments.append("Корректное значение города")
        
        # Проверяем наличие опционального аргумента date
        if "date" in args:
            score += 1
            comments.append("Присутствует опциональный аргумент 'date'")
            
            # Проверяем значение date
            if "завтра" in args["date"].lower() or "tomorrow" in args["date"].lower():
                score += 1
                comments.append("Корректное значение даты")
    except json.JSONDecodeError:
        comments.append("Невозможно разобрать аргументы как JSON")
    
    # Общая оценка
    comment = "Отлично" if score >= 4 else "Хорошо" if score >= 3 else "Удовлетворительно"
    
    return {
        "score": score,
        "max_score": 5,
        "comment": comment,
        "details": comments
    }

def analyze_streaming_quality(text):
    """
    Анализирует качество потокового ответа для объяснения алгоритма сортировки слиянием.
    
    Args:
        text: Полный текст ответа
        
    Returns:
        dict: Оценка качества потокового ответа
    """
    score = 0
    comments = []
    
    # Проверяем наличие структурированных секций из оптимизированного формата
    sections = ["КОНЦЕПЦИЯ:", "СЛОЖНОСТЬ:", "АЛГОРИТМ:", "ПРАКТИЧЕСКИЙ ПРИМЕР:", "ЗАКЛЮЧЕНИЕ:"]
    for section in sections:
        if section in text:
            score += 1
            comments.append(f"Присутствует раздел '{section[:-1]}'")
    
    # Проверяем наличие описания алгоритма
    if "сортировк" in text.lower() and "слияни" in text.lower():
        score += 1
        comments.append("Присутствует описание сортировки слиянием")
    
    # Проверяем наличие примера
    if "[8, 3, 5, 1, 9, 2]" in text:
        score += 1
        comments.append("Использован указанный в задаче массив")
    
    # Проверяем наличие шагов алгоритма
    if "разделение" in text.lower() or "слияние" in text.lower() or "merge" in text.lower() or "split" in text.lower():
        score += 1
        comments.append("Описаны ключевые шаги алгоритма")
    
    # Проверяем структуру ответа
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 4:
        score += 1
        comments.append("Хорошая структура с несколькими параграфами")
    
    # Проверяем наличие пояснений о сложности
    if "O(n log n)" in text:
        score += 1
        comments.append("Правильно указана временная сложность алгоритма")
    
    # Общая оценка
    comment = "Отлично" if score >= 8 else "Хорошо" if score >= 5 else "Удовлетворительно"
    
    return {
        "score": score,
        "max_score": 10,  # Увеличено из-за дополнительных критериев
        "comment": comment,
        "details": comments
    }

def run_reasoning_tests():
    """
    Запускает все тесты возможностей рассуждения.
    
    Returns:
        bool: True, если все тесты выполнены (не обязательно успешно)
    """
    print("Тестирование возможностей рассуждения LlamaCPP API...")
    
    # Получаем URL и API ключ из .env
    api_url = get_env("llamacpp_api_base", "http://localhost:8080/v1")
    api_key = get_env("llamacpp_api_key", "NA")
    
    # Проверяем, что URL задан
    if not api_url:
        print("ОШИБКА: URL для LlamaCPP API не найден в .env файле!")
        return False
    
    print(f"Используемый URL LlamaCPP API: {api_url}")
    
    # Создаем директорию для результатов, если её нет
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'outputs', 'api_test_results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Формируем имя файла для результатов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"reasoning_api_test_{timestamp}.json")
    
    # Запускаем все тесты и собираем результаты
    results = {
        "timestamp": datetime.now().isoformat(),
        "api_url": api_url,
        "tests": {}
    }
    
    # Запускаем фоновый мониторинг температуры
    start_temperature_monitoring(monitoring_interval=5.0)
    
    # Получаем начальную температуру
    server_monitor = get_server_monitor()
    initial_temp = server_monitor.check_temperature()
    log_action(f"Начальная температура перед тестами: CPU {initial_temp['cpu_temp']:.1f}°C, GPU {initial_temp['gpu_temp']:.1f}°C")
    
    # Тест 1: Прямое рассуждение
    print("\n1. Тестирование прямых рассуждений...")
    results["tests"]["direct_reasoning"] = test_direct_reasoning(api_url, api_key)
    print("Завершено тестирование прямых рассуждений.")
    
    # Пауза между тестами для снижения нагрузки
    log_action(f"Пауза между тестами {PAUSE_BETWEEN_TESTS} секунд")
    time.sleep(PAUSE_BETWEEN_TESTS)
    
    # Тест 2: Функциональные вызовы
    print("\n2. Тестирование функциональных вызовов...")
    results["tests"]["function_calling"] = test_function_calling(api_url, api_key)
    print("Завершено тестирование функциональных вызовов.")
    
    # Пауза между тестами для снижения нагрузки
    log_action(f"Пауза между тестами {PAUSE_BETWEEN_TESTS} секунд")
    time.sleep(PAUSE_BETWEEN_TESTS)
    
    # Тест 3: Потоковая передача
    print("\n3. Тестирование потоковой передачи рассуждений...")
    results["tests"]["stream_reasoning"] = test_stream_reasoning(api_url, api_key)
    print("Завершено тестирование потоковой передачи.")
    
    # Получаем финальную температуру
    final_temp = server_monitor.check_temperature()
    log_action(f"Финальная температура после тестов: CPU {final_temp['cpu_temp']:.1f}°C, GPU {final_temp['gpu_temp']:.1f}°C")
    
    # Добавляем информацию о температуре в результаты
    results["temperature"] = {
        "initial": {
            "cpu": initial_temp["cpu_temp"],
            "gpu": initial_temp["gpu_temp"]
        },
        "final": {
            "cpu": final_temp["cpu_temp"],
            "gpu": final_temp["gpu_temp"]
        }
    }
    
    # Сохраняем результаты в файл
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nВсе тесты завершены. Результаты сохранены в файл: {results_file}")
    
    # Выводим краткую статистику
    success_count = sum(1 for test in results["tests"].values() if test.get("success", False))
    total_count = len(results["tests"])
    
    print(f"\nСтатистика выполнения: {success_count}/{total_count} тестов успешно выполнены")
    
    return True

if __name__ == "__main__":
    print("Тестирование возможностей рассуждения (reasoning) LlamaCPP API")
    print("=" * 80)
    
    # Инициализируем логирование
    setup_logging()
    log_action("Запуск тестирования возможностей рассуждения LlamaCPP API с оптимизированными промптами")
    
    success = run_reasoning_tests()
    
    if success:
        log_result("Тестирование возможностей рассуждения выполнено")
        print("\nТЕСТЫ ЗАВЕРШЕНЫ: Проверка возможностей рассуждения через LlamaCPP API выполнена!")
        sys.exit(0)
    else:
        log_error("Возникли проблемы при запуске тестов рассуждения")
        print("\nТЕСТЫ НЕ ВЫПОЛНЕНЫ: Возникли проблемы при запуске тестов рассуждения.")
        sys.exit(1)