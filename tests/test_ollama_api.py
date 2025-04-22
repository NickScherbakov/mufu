"""
Тестирование доступности API Ollama.
Этот скрипт проверяет, что приложение может корректно подключиться
к API Ollama с использованием настроек из файла .env
"""
import os
import sys

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
from app.utils import get_env

def test_ollama_api():
    """Проверяет доступность API Ollama."""
    print("Тестирование подключения к API Ollama...")
    
    # Получаем URL и API ключ из .env
    ollama_url = get_env("ollama_api_base", "http://localhost:11434")
    ollama_api_key = get_env("ollama_api_key", "NA")
    
    # Проверяем, что URL задан
    if not ollama_url:
        print("ОШИБКА: URL для Ollama API не найден в .env файле!")
        return False
    
    print(f"Используемый URL Ollama API: {ollama_url}")
    
    # Формируем URL для проверки статуса
    api_status_url = f"{ollama_url.rstrip('/')}/api/tags"
    
    # Формируем заголовки запроса
    headers = {}
    if ollama_api_key and ollama_api_key != "NA":
        headers["Authorization"] = f"Bearer {ollama_api_key}"
    
    try:
        print(f"Отправка запроса к {api_status_url}...")
        response = requests.get(api_status_url, headers=headers)
        response.raise_for_status()  # Проверка на HTTP ошибки
        
        # Пытаемся разобрать ответ как JSON
        result = response.json()
        
        print("\nСписок доступных моделей:")
        if "models" in result:
            # Формат ответа в более новых версиях Ollama
            for model in result["models"]:
                print(f"- {model['name']} ({model.get('size', 'N/A')})")
        else:
            # Формат ответа в API списка тегов
            for model in result.get("models", []):
                print(f"- {model}")
        
        print("\nСоединение с Ollama API установлено успешно!")
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"\nОШИБКА: Не удалось подключиться к Ollama API по адресу {ollama_url}.")
        print("Убедитесь, что:")
        print("1. Сервер Ollama запущен")
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
        print(f"\nНепредвиденная ошибка при проверке Ollama API: {e}")
        return False

if __name__ == "__main__":
    print("Тестирование подключения к API Ollama")
    print("=" * 80)
    
    success = test_ollama_api()
    
    if success:
        print("\nТЕСТ ПРОЙДЕН: API Ollama доступен и работает корректно!")
        sys.exit(0)
    else:
        print("\nТЕСТ НЕ ПРОЙДЕН: Возникли проблемы при работе с API Ollama.")
        sys.exit(1)