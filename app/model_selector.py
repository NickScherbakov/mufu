"""
Модуль для интеллектуального выбора модели и API в зависимости от типа задачи.
Обеспечивает оптимальный выбор модели для различных типов контента (текст, код и т.д.)
и помогает получать информацию о возможностях моделей.
"""

import os
import re
import requests
import json
from pathlib import Path
from .utils import get_env
from .logger import log_action, log_decision, log_result, log_error

# Типы контента
CONTENT_TYPE_GENERAL = "general"  # Общий текст
CONTENT_TYPE_CODE = "code"        # Программный код
CONTENT_TYPE_SUMMARY = "summary"  # Суммаризация/сокращение текста

# Типы API
API_TYPE_OLLAMA = "ollama"
API_TYPE_LLAMACPP = "llamacpp"
API_TYPE_YANDEXGPT = "yandexgpt"

class ModelSelector:
    """Класс для выбора оптимальной модели и API для обработки контента."""
    
    def __init__(self):
        """Инициализирует селектор моделей с настройками из .env."""
        # Загружаем настройки приоритетов API
        self.text_api_priority = get_env("text_api_priority", "ollama,llamacpp,yandexgpt").split(",")
        self.code_api_priority = get_env("code_api_priority", "ollama,llamacpp,yandexgpt").split(",")
        
        # Загружаем настройки моделей по умолчанию
        self.default_models = {
            API_TYPE_OLLAMA: {
                CONTENT_TYPE_GENERAL: get_env("ollama_default_model", "llama3"),
                CONTENT_TYPE_CODE: get_env("ollama_code_model", "codellama"),
                CONTENT_TYPE_SUMMARY: get_env("ollama_text_model", "llama3"),
            },
            API_TYPE_LLAMACPP: {
                CONTENT_TYPE_GENERAL: get_env("llamacpp_default_model", ""),
                CONTENT_TYPE_CODE: get_env("llamacpp_default_model", ""),
                CONTENT_TYPE_SUMMARY: get_env("llamacpp_default_model", ""),
            },
            API_TYPE_YANDEXGPT: {
                CONTENT_TYPE_GENERAL: get_env("yandexgpt_model", "yandexgpt"),
                CONTENT_TYPE_CODE: get_env("yandexgpt_model", "yandexgpt"),
                CONTENT_TYPE_SUMMARY: get_env("yandexgpt_model", "yandexgpt"),
            },
        }
        
        # Загружаем базовые URL для API
        self.api_base_urls = {
            API_TYPE_OLLAMA: get_env("ollama_api_base", "http://localhost:11434"),
            API_TYPE_LLAMACPP: get_env("llamacpp_api_base", "http://localhost:8080/v1"),
            API_TYPE_YANDEXGPT: get_env("yandexgpt_url", "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"),
        }
        
        # Загружаем API ключи
        self.api_keys = {
            API_TYPE_OLLAMA: get_env("ollama_api_key", "NA"),
            API_TYPE_LLAMACPP: get_env("llamacpp_api_key", "NA"),
            API_TYPE_YANDEXGPT: get_env("yandexgpt_api_key", ""),
        }
        
        # Дополнительные параметры для YandexGPT
        self.yandexgpt_folder_id = get_env("yandexgpt_folder_id", "")
        
        # Кэш для хранения информации о доступности API и моделях
        self.api_availability_cache = {}
        self.model_capabilities_cache = {}
    
    def detect_content_type(self, text):
        """
        Определяет тип контента по тексту.
        
        Args:
            text: Текст для анализа
            
        Returns:
            str: Тип контента (CONTENT_TYPE_*)
        """
        # Проверяем, похож ли текст на код
        code_indicators = [
            r'(def|class|function)\s+\w+\s*\(.*\)\s*(\{|\:)',  # Определение функций/классов
            r'(if|for|while)\s*\(.*\)\s*(\{|\:)',  # Управляющие конструкции
            r'(var|let|const|int|float|double|string|bool)\s+\w+\s*=',  # Определение переменных
            r'import\s+[\w\s\{\},\.]+\s+from',  # импорты в JS/TS/Python
            r'#include\s+[<"].*[>"]',  # C/C++ инклюды
            r'public\s+(static\s+)?(class|void|int|String)',  # Java конструкции
            r'<\w+(\s+\w+=".*")*>.*</\w+>',  # HTML/XML теги
        ]
        
        for pattern in code_indicators:
            if re.search(pattern, text):
                return CONTENT_TYPE_CODE
        
        # Проверяем, нужно ли суммаризировать текст (более 1000 символов или есть маркеры для суммаризации)
        summarization_indicators = [
            r'(summarize|summary|кратко|резюме|тезисы)',
            r'(TL;DR|TLDR)',
        ]
        
        if len(text) > 1000:
            for pattern in summarization_indicators:
                if re.search(pattern, text, re.IGNORECASE):
                    return CONTENT_TYPE_SUMMARY
        
        # По умолчанию считаем, что это обычный текст
        return CONTENT_TYPE_GENERAL
    
    def select_optimal_api_and_model(self, text, preferred_api=None, preferred_model=None):
        """
        Выбирает оптимальный API и модель для обработки заданного текста.
        
        Args:
            text: Текст для обработки
            preferred_api: Предпочтительный API (если указан)
            preferred_model: Предпочтительная модель (если указана)
            
        Returns:
            tuple: (api_type, model_name, api_base_url)
        """
        log_action("Выбор оптимального API и модели для обработки текста")
        
        # Если указаны предпочтительные API и модель, используем их
        if preferred_api and preferred_model:
            log_decision(f"Использование указанных API ({preferred_api}) и модели ({preferred_model})", 
                         reasoning="Явно указаны в параметрах")
            return preferred_api, preferred_model, self.api_base_urls.get(preferred_api, "")
        
        # Определяем тип контента
        content_type = self.detect_content_type(text)
        log_info = {"content_type": content_type, "text_length": len(text)}
        
        if content_type == CONTENT_TYPE_CODE:
            api_priority = self.code_api_priority
            log_info["detected_as"] = "программный код"
        elif content_type == CONTENT_TYPE_SUMMARY:
            api_priority = self.text_api_priority  # Используем тот же приоритет, но другие модели
            log_info["detected_as"] = "текст для суммаризации"
        else:
            api_priority = self.text_api_priority
            log_info["detected_as"] = "обычный текст"
        
        # Если указан предпочтительный API, ставим его в начало списка
        if preferred_api and preferred_api in api_priority:
            api_priority = [preferred_api] + [api for api in api_priority if api != preferred_api]
        
        # Проверяем доступность API в порядке приоритета
        for api_type in api_priority:
            # Проверяем доступность API (с использованием кэша)
            is_available = self.check_api_availability(api_type)
            
            if is_available:
                # Выбираем модель для данного API и типа контента
                if preferred_model:
                    model_name = preferred_model
                else:
                    model_name = self.default_models[api_type][content_type]
                
                api_url = self.api_base_urls[api_type]
                
                log_decision(f"Выбор API {api_type} с моделью {model_name}", 
                             reasoning=f"API доступен и поддерживает обработку {log_info['detected_as']}")
                
                log_result("Выбран оптимальный API и модель", {
                    "api": api_type,
                    "model": model_name,
                    "content_type": content_type,
                })
                
                return api_type, model_name, api_url
        
        # Если ни один API не доступен, возвращаем значение по умолчанию
        log_error("Не удалось найти доступный API", 
                 Exception("Ни один из настроенных API не доступен"))
        
        return None, None, None
    
    def check_api_availability(self, api_type):
        """
        Проверяет доступность API.
        
        Args:
            api_type: Тип API для проверки
            
        Returns:
            bool: True, если API доступен
        """
        # Если информация о доступности есть в кэше и она актуальная, используем её
        if api_type in self.api_availability_cache:
            # Возвращаем закэшированный результат
            return self.api_availability_cache[api_type]
        
        log_action(f"Проверка доступности API {api_type}")
        
        try:
            if api_type == API_TYPE_OLLAMA:
                # Для Ollama делаем запрос к /api/tags
                url = f"{self.api_base_urls[api_type].rstrip('/')}/api/tags"
                headers = {}
                if self.api_keys[api_type] and self.api_keys[api_type] != "NA":
                    headers["Authorization"] = f"Bearer {self.api_keys[api_type]}"
                
                response = requests.get(url, headers=headers, timeout=5)
                is_available = response.status_code == 200
                
            elif api_type == API_TYPE_LLAMACPP:
                # Для LlamaCPP делаем запрос к /models
                url = f"{self.api_base_urls[api_type].rstrip('/')}/models"
                headers = {}
                if self.api_keys[api_type] and self.api_keys[api_type] != "NA":
                    headers["Authorization"] = f"Bearer {self.api_keys[api_type]}"
                
                response = requests.get(url, headers=headers, timeout=5)
                is_available = response.status_code == 200
                
            elif api_type == API_TYPE_YANDEXGPT:
                # Для YandexGPT делаем простой запрос с минимальными токенами
                url = self.api_base_urls[api_type]
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Api-Key {self.api_keys[api_type]}",
                    "x-folder-id": self.yandexgpt_folder_id
                }
                
                payload = {
                    "modelUri": f"gpt://{self.yandexgpt_folder_id}/{self.default_models[api_type][CONTENT_TYPE_GENERAL]}",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": 1  # Минимальное количество токенов для проверки
                    },
                    "messages": [
                        {
                            "role": "user",
                            "text": "Проверка"
                        }
                    ]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=5)
                is_available = response.status_code == 200
            else:
                is_available = False
            
            # Сохраняем результат в кэш
            self.api_availability_cache[api_type] = is_available
            
            if is_available:
                log_result(f"API {api_type} доступен")
            else:
                log_error(f"API {api_type} недоступен", 
                         Exception(f"HTTP статус: {response.status_code}"))
            
            return is_available
            
        except Exception as e:
            log_error(f"Ошибка при проверке доступности API {api_type}", e)
            self.api_availability_cache[api_type] = False
            return False
    
    def get_model_capabilities(self, api_type, model_name):
        """
        Получает информацию о возможностях модели.
        
        Args:
            api_type: Тип API
            model_name: Название модели
            
        Returns:
            dict: Словарь с информацией о возможностях модели
        """
        cache_key = f"{api_type}:{model_name}"
        
        # Проверяем кэш
        if cache_key in self.model_capabilities_cache:
            return self.model_capabilities_cache[cache_key]
        
        log_action(f"Запрос информации о возможностях модели {model_name} через {api_type}")
        
        capabilities = {
            "name": model_name,
            "api": api_type,
            "supports_code": False,
            "supports_summarization": False,
            "max_tokens": 2048,  # Значение по умолчанию
            "description": "",
            "version": "Неизвестно"
        }
        
        try:
            if api_type == API_TYPE_OLLAMA:
                # Для Ollama запрашиваем информацию через /api/show
                url = f"{self.api_base_urls[api_type].rstrip('/')}/api/show"
                headers = {}
                if self.api_keys[api_type] and self.api_keys[api_type] != "NA":
                    headers["Authorization"] = f"Bearer {self.api_keys[api_type]}"
                
                payload = {"name": model_name}
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    model_info = response.json()
                    
                    # Парсим информацию о модели
                    if "parameters" in model_info and isinstance(model_info["parameters"], dict):
                        if "num_ctx" in model_info["parameters"]:
                            capabilities["max_tokens"] = int(model_info["parameters"]["num_ctx"])
                    
                    # Определяем поддерживаемые возможности по имени модели
                    capabilities["supports_code"] = any(code_indicator in model_name.lower() 
                                                      for code_indicator in ["code", "coder", "starcoder", "wizard"])
                    capabilities["supports_summarization"] = True  # Большинство моделей поддерживают
                    
            elif api_type == API_TYPE_LLAMACPP:
                # Для LlamaCPP определяем возможности по имени модели
                # (т.к. нет стандартного API для получения свойств)
                capabilities["supports_code"] = any(code_indicator in model_name.lower() 
                                                  for code_indicator in ["code", "coder", "starcoder", "wizard"])
                capabilities["supports_summarization"] = True
                
            elif api_type == API_TYPE_YANDEXGPT:
                # Для YandexGPT запрашиваем информацию у самой модели
                url = self.api_base_urls[api_type]
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Api-Key {self.api_keys[api_type]}",
                    "x-folder-id": self.yandexgpt_folder_id
                }
                
                payload = {
                    "modelUri": f"gpt://{self.yandexgpt_folder_id}/{model_name}",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": 100
                    },
                    "messages": [
                        {
                            "role": "user",
                            "text": "Пожалуйста, опиши свои возможности. Укажи, поддерживаешь ли ты работу с программным кодом и суммаризацию текста. Какое максимальное количество токенов ты можешь обработать?"
                        }
                    ]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "result" in result and "alternatives" in result["result"] and len(result["result"]["alternatives"]) > 0:
                        message = result["result"]["alternatives"][0].get("message", {})
                        response_text = message.get("text", "")
                        
                        capabilities["description"] = response_text
                        
                        # Извлекаем информацию из ответа модели
                        capabilities["supports_code"] = "код" in response_text.lower() or "программирован" in response_text.lower()
                        capabilities["supports_summarization"] = "суммариз" in response_text.lower() or "резюм" in response_text.lower()
                        
                        # Пытаемся найти упоминание о максимальном количестве токенов
                        token_matches = re.search(r'(\d{1,6})\s*(токенов|tokens)', response_text, re.IGNORECASE)
                        if token_matches:
                            capabilities["max_tokens"] = int(token_matches.group(1))
                        
                        capabilities["version"] = result["result"].get("modelVersion", "Неизвестно")
            
            # Сохраняем результат в кэш
            self.model_capabilities_cache[cache_key] = capabilities
            
            log_result(f"Получена информация о возможностях модели {model_name}", {
                "supports_code": capabilities["supports_code"],
                "supports_summarization": capabilities["supports_summarization"],
                "max_tokens": capabilities["max_tokens"]
            })
            
            return capabilities
            
        except Exception as e:
            log_error(f"Ошибка при получении информации о модели {model_name}", e)
            
            # Сохраняем базовую информацию в кэш, чтобы не делать повторные запросы
            self.model_capabilities_cache[cache_key] = capabilities
            return capabilities

# Создаем экземпляр селектора моделей для использования в других модулях
model_selector = ModelSelector()

if __name__ == "__main__":
    # Пример использования
    from app.logger import setup_logging
    
    setup_logging()
    selector = ModelSelector()
    
    # Пример текста для анализа
    code_sample = """
    def calculate_sum(a, b):
        return a + b
        
    result = calculate_sum(10, 20)
    print(f"Result: {result}")
    """
    
    text_sample = """
    Искусственный интеллект (ИИ) — это область компьютерных наук, которая занимается моделированием интеллектуальных процессов
    с помощью компьютерных систем. Основные направления исследований в ИИ включают машинное обучение, 
    обработку естественного языка, компьютерное зрение и робототехнику.
    """
    
    # Определяем тип контента
    print(f"Тип кода: {selector.detect_content_type(code_sample)}")
    print(f"Тип текста: {selector.detect_content_type(text_sample)}")
    
    # Выбираем оптимальную модель для кода
    api_type, model_name, api_url = selector.select_optimal_api_and_model(code_sample)
    print(f"Для кода: API={api_type}, модель={model_name}")
    
    # Выбираем оптимальную модель для текста
    api_type, model_name, api_url = selector.select_optimal_api_and_model(text_sample)
    print(f"Для текста: API={api_type}, модель={model_name}")
    
    # Получаем возможности модели
    if api_type and model_name:
        capabilities = selector.get_model_capabilities(api_type, model_name)
        print(f"Возможности модели {model_name}:")
        print(f"- Поддержка кода: {'Да' if capabilities['supports_code'] else 'Нет'}")
        print(f"- Поддержка суммаризации: {'Да' if capabilities['supports_summarization'] else 'Нет'}")
        print(f"- Максимальное количество токенов: {capabilities['max_tokens']}")