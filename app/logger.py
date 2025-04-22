"""
Модуль логирования для проекта MUFU.

Обеспечивает структурированное логирование информации о ходе выполнения проекта,
включая цели, действия, решения и результаты. Логи сохраняются в формате,
удобном для чтения как людьми, так и ИИ.
"""

import logging
import json
import os
import datetime
import inspect
import traceback
from pathlib import Path
import yaml

# Константы для типов событий
EVENT_GOAL = "GOAL"        # Цель действия
EVENT_ACTION = "ACTION"    # Выполняемое действие
EVENT_DECISION = "DECISION"  # Принятое решение
EVENT_RESULT = "RESULT"    # Результат действия
EVENT_ERROR = "ERROR"      # Ошибка
EVENT_INFO = "INFO"        # Информационное сообщение

# Настройки
LOG_DIR = Path("logs")
LOG_FILE_FORMAT = "chatgpt_video_{date}.log"
LOG_FORMAT_TEXT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_FORMAT_JSON = "%(asctime)s %(message)s"

# Словарь логгеров
loggers = {}


def setup_logging(log_to_console=True, log_level=logging.INFO):
    """
    Настройка системы логирования.
    
    Args:
        log_to_console: Выводить ли логи в консоль
        log_level: Уровень логирования
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    global loggers
    
    # Создаем директорию для логов, если её нет
    if not LOG_DIR.exists():
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Имя файла с текущей датой
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_filename = LOG_DIR / LOG_FILE_FORMAT.format(date=date_str)
    
    # Создаем базовый логгер
    logger = logging.getLogger("chatgpt_video")
    if logger.handlers:  # Если логгер уже настроен, используем существующий
        return logger
    
    logger.setLevel(log_level)
    logger.propagate = False
    
    # Форматтер для обычных текстовых логов
    formatter_text = logging.Formatter(LOG_FORMAT_TEXT)
    
    # Обработчик для текстового файла
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(formatter_text)
    logger.addHandler(file_handler)
    
    # Создаем JSON-логгер
    json_logger = logging.getLogger("chatgpt_video_json")
    json_logger.setLevel(log_level)
    json_logger.propagate = False
    
    # JSON файл
    json_filename = LOG_DIR / f"json_{date_str}.log"
    json_handler = logging.FileHandler(json_filename, encoding='utf-8')
    json_handler.setFormatter(logging.Formatter(LOG_FORMAT_JSON))
    json_logger.addHandler(json_handler)
    
    # Консольный вывод (опционально)
    if log_to_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter_text)
        logger.addHandler(console)
    
    # Сохраняем логгеры в словарь
    loggers = {
        "text": logger,
        "json": json_logger
    }
    
    # Записываем начальное сообщение
    log_info("Система логирования инициализирована", 
             context={"log_file": str(log_filename), "json_file": str(json_filename)})
    
    return logger


def _get_caller_info():
    """Получает информацию о вызывающей функции."""
    # Получаем стек вызовов (frame, filename, line_number, function_name, lines, index)
    stack = inspect.stack()[2]  # 2 - пропускаем текущую функцию и непосредственного вызывающего
    return {
        "file": os.path.basename(stack.filename),
        "function": stack.function,
        "line": stack.lineno
    }


def _log_structured(event_type, message, context=None, level=logging.INFO):
    """
    Внутренняя функция для структурированного логирования.
    
    Args:
        event_type: Тип события (GOAL, ACTION, DECISION, RESULT, ERROR)
        message: Основное сообщение
        context: Словарь с дополнительной информацией
        level: Уровень логирования
    """
    global loggers
    if not loggers:
        setup_logging()
    
    # Получаем информацию о вызывающей функции
    caller_info = _get_caller_info()
    
    # Форматируем основное текстовое сообщение
    text_message = f"[{event_type}] {message}"
    loggers["text"].log(level, text_message)
    
    # Создаем структурированный JSON
    log_data = {
        "type": event_type,
        "message": message,
        "caller": caller_info
    }
    
    # Добавляем контекст, если он есть
    if context:
        log_data["context"] = context
    
    # Записываем JSON
    loggers["json"].log(level, json.dumps(log_data, ensure_ascii=False))


def log_goal(goal, details=None):
    """
    Логирует цель или намерение действия.
    
    Args:
        goal: Описание цели
        details: Дополнительные детали о цели
    """
    context = {"details": details} if details else None
    _log_structured(EVENT_GOAL, goal, context)


def log_action(action, params=None):
    """
    Логирует выполняемое действие.
    
    Args:
        action: Описание действия
        params: Параметры действия
    """
    context = {"params": params} if params else None
    _log_structured(EVENT_ACTION, action, context)


def log_decision(decision, alternatives=None, reasoning=None):
    """
    Логирует принятое решение.
    
    Args:
        decision: Принятое решение
        alternatives: Альтернативные решения, которые были рассмотрены
        reasoning: Обоснование решения
    """
    context = {}
    if alternatives:
        context["alternatives"] = alternatives
    if reasoning:
        context["reasoning"] = reasoning
    
    _log_structured(EVENT_DECISION, decision, context)


def log_result(result, metrics=None):
    """
    Логирует результат действия.
    
    Args:
        result: Описание результата
        metrics: Метрики или измерения результата
    """
    context = {"metrics": metrics} if metrics else None
    _log_structured(EVENT_RESULT, result, context)


def log_error(error, exception=None):
    """
    Логирует ошибку.
    
    Args:
        error: Описание ошибки
        exception: Исключение, если есть
    """
    context = None
    if exception:
        context = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc()
        }
    
    _log_structured(EVENT_ERROR, error, context, level=logging.ERROR)


def log_info(message, context=None):
    """
    Логирует информационное сообщение.
    
    Args:
        message: Информационное сообщение
        context: Дополнительный контекст
    """
    _log_structured(EVENT_INFO, message, context)


def export_session_log(format="yaml"):
    """
    Экспортирует текущую сессию логов в структурированном формате.
    
    Args:
        format: Формат экспорта ('yaml' или 'json')
        
    Returns:
        str: Путь к созданному файлу
    """
    # Получаем текущие логи из JSON файла
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    json_filename = LOG_DIR / f"json_{date_str}.log"
    
    if not os.path.exists(json_filename):
        return None
    
    # Читаем JSON логи
    log_entries = []
    with open(json_filename, 'r', encoding='utf-8') as f:
        for line in f:
            # Пропуск timestamp от логгера
            parts = line.strip().split(' ', 1)
            if len(parts) > 1:
                try:
                    entry = json.loads(parts[1])
                    log_entries.append(entry)
                except json.JSONDecodeError:
                    continue
    
    # Создаем файл экспорта
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if format.lower() == "yaml":
        export_file = LOG_DIR / f"session_log_{timestamp}.yaml"
        with open(export_file, 'w', encoding='utf-8') as f:
            yaml.dump(log_entries, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    else:
        export_file = LOG_DIR / f"session_log_{timestamp}.json"
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(log_entries, f, indent=2, ensure_ascii=False)
    
    return str(export_file)


def get_session_summary():
    """
    Создает краткую сводку текущей сессии логирования.
    
    Returns:
        dict: Словарь со сводной информацией о сессии
    """
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    json_filename = LOG_DIR / f"json_{date_str}.log"
    
    if not os.path.exists(json_filename):
        return {"error": "Log file not found"}
    
    # Счетчики по типам событий
    counters = {
        "GOAL": 0,
        "ACTION": 0,
        "DECISION": 0,
        "RESULT": 0,
        "ERROR": 0,
        "INFO": 0
    }
    
    # Последние события каждого типа
    latest = {}
    
    # Читаем JSON логи
    with open(json_filename, 'r', encoding='utf-8') as f:
        for line in f:
            # Пропуск timestamp от логгера
            parts = line.strip().split(' ', 1)
            if len(parts) > 1:
                try:
                    entry = json.loads(parts[1])
                    event_type = entry.get("type")
                    if event_type in counters:
                        counters[event_type] += 1
                        latest[event_type] = entry
                except (json.JSONDecodeError, KeyError):
                    continue
    
    # Формируем сводку
    summary = {
        "date": date_str,
        "counts": counters,
        "total_events": sum(counters.values()),
        "latest_error": latest.get("ERROR"),
        "latest_result": latest.get("RESULT")
    }
    
    return summary


if __name__ == "__main__":
    # Пример использования
    setup_logging()
    log_goal("Демонстрация работы логгера")
    log_action("Вызов тестовых функций логирования")
    log_decision("Использовать текстовый и JSON формат логов", 
                reasoning="Текстовый формат удобен для чтения людьми, JSON - для машинной обработки")
    log_result("Логи успешно записаны")
    print("Модуль логирования протестирован. Проверьте файлы логов в директории logs/")