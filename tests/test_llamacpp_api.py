"""
Тестирование доступности API LlamaCPP.
Этот скрипт проверяет, что приложение может корректно подключиться
к API LlamaCPP с использованием настроек из файла .env
"""
import os
import sys

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from app.utils import get_env
from app.logger import setup_logging, log_action, log_result, log_error

def test_llamacpp_api():
    """Проверяет доступность API LlamaCPP."""
    print("Тестирование подключения к API LlamaCPP...")
    
    # Получаем URL и API ключ из .env
    llamacpp_url = get_env("llamacpp_api_base", "http://localhost:8080/v1")
    llamacpp_api_key = get_env("llamacpp_api_key", "NA")
    
    # Проверяем, что URL задан
    if not llamacpp_url:
        print("ОШИБКА: URL для LlamaCPP API не найден в .env файле!")
        return False
    
    print(f"Используемый URL LlamaCPP API: {llamacpp_url}")
    
    # Формируем URL для проверки статуса
    api_models_url = f"{llamacpp_url.rstrip('/')}/models"
    
    # Формируем заголовки запроса
    headers = {}
    if llamacpp_api_key and llamacpp_api_key != "NA":
        headers["Authorization"] = f"Bearer {llamacpp_api_key}"
    
    try:
        print(f"Отправка запроса к {api_models_url}...")
        response = requests.get(api_models_url, headers=headers)
        response.raise_for_status()  # Проверка на HTTP ошибки
        
        # Пытаемся разобрать ответ как JSON
        result = response.json()
        
        print("\nИнформация о моделях:")
        if "data" in result:
            # Формат ответа, совместимый с OpenAI API
            for model in result["data"]:
                model_id = model.get("id", "Неизвестно")
                owned_by = model.get("owned_by", "Неизвестно")
                print(f"- {model_id} (владелец: {owned_by})")
        else:
            # Альтернативный формат
            print(f"- Получена информация о моделях: {json.dumps(result, indent=2)}")
        
        # Также попробуем отправить простой запрос на завершение текста
        print("\nПроверка запроса на генерацию текста...")
        completion_url = f"{llamacpp_url.rstrip('/')}/completions"
        
        payload = {
            "prompt": "Привет, это тестовый запрос",
            "max_tokens": 10,
            "temperature": 0.7
        }
        
        response = requests.post(completion_url, json=payload, headers=headers)
        response.raise_for_status()
        completion_result = response.json()
        
        # Выводим результат
        if "choices" in completion_result and len(completion_result["choices"]) > 0:
            text = completion_result["choices"][0].get("text", "")
            print(f"Получен ответ: {text}")
        elif "completion" in completion_result:
            print(f"Получен ответ: {completion_result['completion']}")
        else:
            print(f"Получен ответ в нестандартном формате: {json.dumps(completion_result, indent=2)}")
        
        print("\nСоединение с LlamaCPP API установлено успешно!")
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"\nОШИБКА: Не удалось подключиться к LlamaCPP API по адресу {llamacpp_url}.")
        print("Убедитесь, что:")
        print("1. Сервер LlamaCPP запущен")
        print("2. URL в .env файле указан правильно")
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
        print(f"\nНепредвиденная ошибка при проверке LlamaCPP API: {e}")
        return False

if __name__ == "__main__":
    print("Тестирование подключения к API LlamaCPP")
    print("=" * 80)
    
    # Инициализируем логирование
    setup_logging()
    log_action("Тестирование подключения к API LlamaCPP")
    
    success = test_llamacpp_api()
    
    if success:
        log_result("API LlamaCPP доступен и работает корректно")
        print("\nТЕСТ ПРОЙДЕН: API LlamaCPP доступен и работает корректно!")
        sys.exit(0)
    else:
        log_error("Возникли проблемы при работе с API LlamaCPP")
        print("\nТЕСТ НЕ ПРОЙДЕН: Возникли проблемы при работе с API LlamaCPP.")
        sys.exit(1)