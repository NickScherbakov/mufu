"""
Скрипт для исследования доступных моделей AI API и их свойств.
Позволяет получить информацию о моделях YandexGPT, LlamaCPP и Ollama.
"""
import os
import sys
import requests
import json
from pprint import pprint
from app.utils import get_env
from app.logger import setup_logging, log_goal, log_action, log_result, log_error

def explore_yandexgpt_models():
    """Исследует доступные модели YandexGPT API."""
    print("\n=== Исследование моделей YandexGPT API ===")
    
    # Получаем ключи доступа из .env
    yandexgpt_api_key = get_env("yandexgpt_api_key", "")
    yandexgpt_folder_id = get_env("yandexgpt_folder_id", "")
    
    if not yandexgpt_api_key or not yandexgpt_folder_id:
        print("ОШИБКА: Не найдены API-ключ или folder_id для YandexGPT в .env файле")
        return False
        
    # Формируем заголовки запроса
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {yandexgpt_api_key}",
        "x-folder-id": yandexgpt_folder_id
    }
    
    # Попытаемся получить информацию о моделях через разные методы API
    
    # Метод 1: Запрос к документированному API для генерации ответа с информацией о модели
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    # Список известных моделей YandexGPT для тестирования
    models_to_test = [
        "yandexgpt", 
        "yandexgpt-lite",
        "summarization"
    ]
    
    available_models = []
    
    print(f"Тестирование доступных моделей YandexGPT...")
    
    for model_name in models_to_test:
        try:
            print(f"\nПроверка модели: {model_name}")
            model_uri = f"gpt://{yandexgpt_folder_id}/{model_name}"
            
            payload = {
                "modelUri": model_uri,
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": 20
                },
                "messages": [
                    {
                        "role": "user",
                        "text": "Пожалуйста, предоставь название своей модели и твои основные свойства и возможности."
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                model_version = result["result"].get("modelVersion", "Неизвестно")
                
                message = result["result"]["alternatives"][0].get("message", {})
                response_text = message.get("text", "")
                
                # Получаем информацию о токенах
                tokens_info = result["result"].get("tokensUsed", {})
                total_tokens = tokens_info.get("totalTokens", "Н/Д")
                input_tokens = tokens_info.get("inputTokens", "Н/Д")
                output_tokens = tokens_info.get("outputTokens", "Н/Д")
                
                print(f"✓ Модель {model_name} доступна")
                print(f"  - Версия: {model_version}")
                print(f"  - Токены: всего={total_tokens}, вход={input_tokens}, выход={output_tokens}")
                print(f"  - Ответ модели: {response_text[:100]}...")
                
                available_models.append({
                    "name": model_name,
                    "uri": model_uri,
                    "version": model_version,
                    "response": response_text
                })
                
            else:
                print(f"✗ Модель {model_name} недоступна или возникла ошибка")
                print(f"  - Код ответа: {response.status_code}")
                
                if response.status_code != 404:  # Если не просто "не найдено"
                    try:
                        error_info = response.json()
                        print(f"  - Подробности: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
                    except:
                        print(f"  - Текст ответа: {response.text[:100]}")
                
        except Exception as e:
            print(f"✗ Ошибка при проверке модели {model_name}: {e}")
    
    # Метод 2: Запрос к API для получения списка моделей (может быть недоступен)
    print("\nПопытка получить список всех моделей через API...")
    
    try:
        models_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/listModels"
        models_response = requests.get(models_url, headers=headers)
        
        if models_response.status_code == 200:
            models_data = models_response.json()
            print("Список всех доступных моделей:")
            pprint(models_data)
        else:
            print(f"Не удалось получить список моделей (код {models_response.status_code})")
            print(f"Ответ: {models_response.text[:200]}")
    except Exception as e:
        print(f"Ошибка при запросе списка моделей: {e}")
    
    # Метод 3: Попытка получить информацию о свойствах модели через специальный запрос
    print("\nПопытка получения свойств моделей...")
    
    for model in available_models:
        try:
            props_url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/modelProperties"
            props_payload = {
                "modelUri": model["uri"]
            }
            
            props_response = requests.post(props_url, headers=headers, json=props_payload)
            
            if props_response.status_code == 200:
                props_data = props_response.json()
                print(f"\nСвойства модели {model['name']}:")
                pprint(props_data)
            else:
                print(f"\nНе удалось получить свойства модели {model['name']} (код {props_response.status_code})")
        except Exception as e:
            print(f"Ошибка при получении свойств модели {model['name']}: {e}")
    
    # Выводим итоговую информацию о доступных моделях
    print("\nИтоговая информация о доступных моделях YandexGPT:")
    for model in available_models:
        print(f"- {model['name']} (версия {model['version']})")
    
    return True

def explore_llamacpp_properties():
    """Исследует свойства LlamaCPP API."""
    print("\n=== Исследование свойств LlamaCPP API ===")
    
    # Получаем URL и API ключ из .env
    llamacpp_url = get_env("llamacpp_api_base", "http://localhost:8080/v1")
    llamacpp_api_key = get_env("llamacpp_api_key", "NA")
    
    # Формируем заголовки запроса
    headers = {}
    if llamacpp_api_key and llamacpp_api_key != "NA":
        headers["Authorization"] = f"Bearer {llamacpp_api_key}"
    
    # Проверяем доступ к API и свойствам
    try:
        # Получаем список моделей
        models_url = f"{llamacpp_url.rstrip('/')}/models"
        models_response = requests.get(models_url, headers=headers)
        models_response.raise_for_status()
        
        models_data = models_response.json()
        print("Доступные модели LlamaCPP:")
        if "data" in models_data:
            for model in models_data["data"]:
                model_id = model.get("id", "Неизвестно")
                print(f"- {model_id}")
        else:
            print(f"Нестандартный формат ответа: {json.dumps(models_data, indent=2)}")
        
        # Получаем свойства модели через /props эндпоинт
        print("\nПроверка свойств моделей через /props...")
        
        props_url = f"{llamacpp_url.rstrip('/')}/props"
        props_response = requests.get(props_url, headers=headers)
        
        if props_response.status_code == 200:
            props_data = props_response.json()
            print("Свойства модели LlamaCPP:")
            pprint(props_data)
        else:
            print(f"Не удалось получить свойства модели (код {props_response.status_code})")
            print(f"Ответ: {props_response.text[:200]}")
            
            # Пробуем альтернативный метод через /model_properties
            alt_props_url = f"{llamacpp_url.rstrip('/')}/model_properties"
            alt_props_response = requests.get(alt_props_url, headers=headers)
            
            if alt_props_response.status_code == 200:
                alt_props_data = alt_props_response.json()
                print("\nСвойства модели через /model_properties:")
                pprint(alt_props_data)
            else:
                print(f"Не удалось получить свойства через /model_properties (код {alt_props_response.status_code})")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при исследовании свойств LlamaCPP API: {e}")
        return False

def explore_ollama_models():
    """Исследует доступные модели и их свойства в Ollama API."""
    print("\n=== Исследование моделей Ollama API ===")
    
    # Получаем URL из .env
    ollama_url = get_env("ollama_api_base", "http://localhost:11434")
    ollama_api_key = get_env("ollama_api_key", "NA")
    
    # Формируем заголовки запроса
    headers = {}
    if ollama_api_key and ollama_api_key != "NA":
        headers["Authorization"] = f"Bearer {ollama_api_key}"
    
    try:
        # Получаем список моделей
        models_url = f"{ollama_url.rstrip('/')}/api/tags"
        models_response = requests.get(models_url, headers=headers)
        models_response.raise_for_status()
        
        models_data = models_response.json()
        
        print("Список доступных моделей Ollama:")
        if "models" in models_data:
            for model in models_data["models"]:
                if isinstance(model, dict):
                    name = model.get("name", "Неизвестно")
                    size = model.get("size", "Н/Д")
                    print(f"- {name} (размер: {size})")
                else:
                    print(f"- {model}")
        else:
            print(f"Нестандартный формат ответа: {json.dumps(models_data, indent=2)}")
        
        # Получаем подробную информацию о каждой модели
        print("\nПолучение подробной информации о моделях...")
        
        # Получим список имен моделей
        model_names = []
        if "models" in models_data:
            for model in models_data["models"]:
                if isinstance(model, dict):
                    model_names.append(model.get("name", ""))
                else:
                    model_names.append(model)
        
        # Для каждой модели получим свойства
        for model_name in model_names:
            if not model_name:
                continue
                
            show_url = f"{ollama_url.rstrip('/')}/api/show"
            show_payload = {"name": model_name}
            
            try:
                show_response = requests.post(show_url, headers=headers, json=show_payload)
                
                if show_response.status_code == 200:
                    model_info = show_response.json()
                    print(f"\nСвойства модели {model_name}:")
                    
                    # Выводим выборочную информацию
                    if "parameters" in model_info:
                        print("Параметры модели:")
                        for key, value in model_info["parameters"].items():
                            print(f"  - {key}: {value}")
                    
                    if "template" in model_info:
                        print(f"Шаблон запросов: {model_info['template'][:50]}...")
                    
                    if "system" in model_info:
                        print(f"Системный промпт: {model_info['system'][:50]}...")
                    
                    if "license" in model_info:
                        print(f"Лицензия: {model_info['license']}")
                else:
                    print(f"Не удалось получить свойства модели {model_name} (код {show_response.status_code})")
            except Exception as e:
                print(f"Ошибка при получении свойств модели {model_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при исследовании моделей Ollama API: {e}")
        return False

def main():
    """Основная функция для запуска исследования моделей."""
    # Настраиваем логирование
    setup_logging()
    log_goal("Исследование свойств моделей AI API")
    
    # Выполняем исследование для каждого API
    try:
        print("=" * 80)
        print("ИССЛЕДОВАНИЕ СВОЙСТВ МОДЕЛЕЙ AI API")
        print("=" * 80)
        
        log_action("Исследование моделей YandexGPT API")
        yandexgpt_success = explore_yandexgpt_models()
        
        log_action("Исследование свойств LlamaCPP API")
        llamacpp_success = explore_llamacpp_properties()
        
        log_action("Исследование моделей Ollama API")
        ollama_success = explore_ollama_models()
        
        print("\n" + "=" * 80)
        print("РЕЗУЛЬТАТЫ ИССЛЕДОВАНИЯ:")
        print(f"YandexGPT API: {'✓ Успешно' if yandexgpt_success else '✗ Неудачно'}")
        print(f"LlamaCPP API: {'✓ Успешно' if llamacpp_success else '✗ Неудачно'}")
        print(f"Ollama API: {'✓ Успешно' if ollama_success else '✗ Неудачно'}")
        print("=" * 80)
        
        log_result("Исследование свойств моделей AI API завершено")
        return True
    except Exception as e:
        log_error(f"Ошибка при исследовании свойств моделей: {str(e)}", e)
        return False

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)