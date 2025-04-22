"""
Тестирование доступности API YandexGPT.
Этот скрипт проверяет, что приложение может корректно подключиться
к API YandexGPT с использованием настроек из файла .env
"""
import os
import sys

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from app.utils import get_env
from app.logger import setup_logging, log_action, log_result, log_error

def test_yandexgpt_api():
    """Проверяет доступность API YandexGPT."""
    print("Тестирование подключения к API YandexGPT...")
    
    # Получаем ключи доступа из .env
    yandexgpt_api_key = get_env("yandexgpt_api_key", "")
    yandexgpt_folder_id = get_env("yandexgpt_folder_id", "")
    yandexgpt_url = get_env("yandexgpt_url", 
                            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion")
    
    # Проверяем, что ключи доступа заданы
    if not yandexgpt_api_key:
        print("ОШИБКА: API-ключ для YandexGPT не найден в .env файле!")
        return False
    
    if not yandexgpt_folder_id:
        print("ОШИБКА: Идентификатор каталога (folder_id) для YandexGPT не найден в .env файле!")
        return False
    
    print(f"Используемый URL YandexGPT API: {yandexgpt_url}")
    print(f"Используемый идентификатор каталога: {yandexgpt_folder_id}")
    print(f"API-ключ: {'*' * 8 + yandexgpt_api_key[-4:] if yandexgpt_api_key else 'не задан'}")
    
    # Получаем информацию о моделях (если возможно)
    print("\nПолучение списка доступных моделей...")
    
    # Формируем заголовки запроса
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {yandexgpt_api_key}",
        "x-folder-id": yandexgpt_folder_id
    }
    
    # Тест 1: Проверка доступа к API через запрос моделей (если такой endpoint доступен)
    try:
        models_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/listModels"
        
        models_response = requests.get(models_url, headers=headers)
        if models_response.status_code == 200:
            models_result = models_response.json()
            print("Доступные модели YandexGPT:")
            if "models" in models_result:
                for model in models_result["models"]:
                    model_id = model.get("id", "Неизвестно")
                    description = model.get("description", "Нет описания")
                    print(f"- {model_id}: {description}")
            else:
                print("Информация о моделях недоступна или имеет другой формат")
        else:
            print(f"Не удалось получить список моделей (код {models_response.status_code})")
    except Exception as e:
        print(f"Не удалось получить список моделей: {e}")
    
    # Тест 2: Проверка генерации текста
    # Настройка используемой модели
    model_name = get_env("yandexgpt_model", "yandexgpt")
    print(f"\nИспользуемая модель для тестирования: {model_name}")
    
    # Формируем тестовый запрос
    payload = {
        "modelUri": f"gpt://{yandexgpt_folder_id}/{model_name}",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 10
        },
        "messages": [
            {
                "role": "user",
                "text": "Привет! Представься, пожалуйста. Какая ты модель?"
            }
        ]
    }
    
    try:
        print(f"Отправка запроса на генерацию текста к {yandexgpt_url}...")
        print(f"URI модели: {payload['modelUri']}")
        
        response = requests.post(yandexgpt_url, headers=headers, json=payload)
        response.raise_for_status()  # Проверка на HTTP ошибки
        
        # Пытаемся разобрать ответ как JSON
        result = response.json()
        
        print("\nИнформация о запросе:")
        
        # Проверяем основные поля в ответе
        if "result" in result and "alternatives" in result["result"] and len(result["result"]["alternatives"]) > 0:
            message = result["result"]["alternatives"][0].get("message", {})
            response_text = message.get("text", "")
            
            # Получаем подробную информацию о модели
            model_details = {
                "uri": payload["modelUri"],
                "version": result["result"].get("modelVersion", "Неизвестно"),
                "usage": {
                    "total_tokens": result["result"].get("tokensUsed", {}).get("totalTokens", "Неизвестно"),
                    "input_tokens": result["result"].get("tokensUsed", {}).get("inputTokens", "Неизвестно"),
                    "output_tokens": result["result"].get("tokensUsed", {}).get("outputTokens", "Неизвестно"),
                }
            }
            
            print(f"Модель: {model_name}")
            print(f"URI модели: {model_details['uri']}")
            print(f"Версия модели: {model_details['version']}")
            print(f"Использованные токены: {model_details['usage']['total_tokens']}")
            print(f"- Входные токены: {model_details['usage']['input_tokens']}")
            print(f"- Выходные токены: {model_details['usage']['output_tokens']}")
            print(f"Полученный ответ: {response_text}")
            
            print("\nСоединение с YandexGPT API установлено успешно!")
            return True
        else:
            print(f"Неожиданный формат ответа: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"\nОШИБКА: Не удалось подключиться к YandexGPT API.")
        print(f"Детали ошибки: {e}")
        return False
        
    except requests.exceptions.HTTPError as e:
        print(f"\nОШИБКА: Сервер вернул ошибку HTTP: {e}")
        print(f"Код ответа: {e.response.status_code}")
        print(f"Содержимое ответа: {e.response.text}")
        return False
        
    except json.JSONDecodeError as e:
        print(f"\nОШИБКА: Не удалось разобрать ответ сервера как JSON.")
        print(f"Полученный ответ: {response.text}")
        print(f"Детали ошибки: {e}")
        return False
        
    except Exception as e:
        print(f"\nНепредвиденная ошибка при проверке YandexGPT API: {e}")
        return False

if __name__ == "__main__":
    print("Тестирование подключения к API YandexGPT")
    print("=" * 80)
    
    # Инициализируем логирование
    setup_logging()
    log_action("Тестирование подключения к API YandexGPT")
    
    success = test_yandexgpt_api()
    
    if success:
        log_result("API YandexGPT доступен и работает корректно")
        print("\nТЕСТ ПРОЙДЕН: API YandexGPT доступен и работает корректно!")
        sys.exit(0)
    else:
        log_error("Возникли проблемы при работе с API YandexGPT")
        print("\nТЕСТ НЕ ПРОЙДЕН: Возникли проблемы при работе с API YandexGPT.")
        sys.exit(1)