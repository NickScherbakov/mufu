import requests
import json
from app.utils import get_env
import os

# Константы загружаем из .env файла
OLLAMA_URL = get_env("ollama_api_base", "http://localhost:11434") + "/api/generate"
OLLAMA_API_KEY = get_env("ollama_api_key", "NA")

LLAMACPP_URL = get_env("llamacpp_api_base", "http://localhost:8080/v1")
LLAMACPP_API_KEY = get_env("llamacpp_api_key", "NA")

YANDEXGPT_API_KEY = get_env("yandexgpt_api_key", "")
YANDEXGPT_FOLDER_ID = get_env("yandexgpt_folder_id", "")
YANDEXGPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

DEFAULT_MODEL = "ollama"  # Возможные значения: "ollama", "llamacpp", "yandexgpt"
DEFAULT_OLLAMA_MODEL = "llama3"  # Модель для Ollama
PROMPT_TEMPLATE = """
Выступай как учитель, который объясняет сложную идею простым языком. Вот блок текста из методики:

"{{исходный_абзац}}"

Преобразуй его в понятное объяснение для школьника.
"""

def simplify(text, engine=DEFAULT_MODEL, model_name=None):
    """
    Упрощает текст с помощью выбранной LLM модели.
    
    Args:
        text: Исходный текст для упрощения
        engine: Движок для упрощения ("ollama", "llamacpp" или "yandexgpt")
        model_name: Имя конкретной модели для выбранного движка (если применимо)
    
    Returns:
        Упрощенный текст или None в случае ошибки
    """
    if engine == "ollama":
        return simplify_with_ollama(text, model_name or DEFAULT_OLLAMA_MODEL)
    elif engine == "llamacpp":
        return simplify_with_llamacpp(text, model_name)
    elif engine == "yandexgpt":
        return simplify_with_yandexgpt(text, model_name)
    else:
        print(f"Ошибка: Неизвестный движок {engine}. Используйте 'ollama', 'llamacpp' или 'yandexgpt'.")
        return None

def simplify_with_ollama(text, model=DEFAULT_OLLAMA_MODEL, ollama_url=OLLAMA_URL):
    """Упрощает текст с помощью LLM через Ollama API."""
    prompt = PROMPT_TEMPLATE.replace("{{исходный_абзац}}", text)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False # Получаем ответ целиком
    }

    try:
        response = requests.post(ollama_url, json=payload)
        response.raise_for_status() # Проверка на HTTP ошибки (4xx, 5xx)

        # Ollama возвращает JSON, где ответ в поле 'response'
        result = response.json()
        simplified_text = result.get('response', '').strip()
        return simplified_text

    except requests.exceptions.ConnectionError:
        print(f"Ошибка: Не удалось подключиться к Ollama по адресу {ollama_url}. Убедитесь, что Ollama запущен.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к Ollama: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось декодировать ответ от Ollama: {response.text}")
        return None
    except Exception as e:
        print(f"Непредвиденная ошибка при упрощении текста через Ollama: {e}")
        return None
        
def simplify_with_llamacpp(text, model=None, llamacpp_url=LLAMACPP_URL, llamacpp_api_key=LLAMACPP_API_KEY):
    """Упрощает текст с помощью LLM через LlamaCPP API."""
    prompt = PROMPT_TEMPLATE.replace("{{исходный_абзац}}", text)

    payload = {
        "prompt": prompt,
        "temperature": 0.7,
        "max_tokens": 512,
        "stop": ["</s>"]  # Стандартный токен остановки для многих LLaMA моделей
    }
    
    headers = {}
    if llamacpp_api_key != "NA":
        headers["Authorization"] = f"Bearer {llamacpp_api_key}"
    
    completion_url = f"{llamacpp_url.rstrip('/')}/completions"
    
    try:
        response = requests.post(completion_url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        # В зависимости от версии llama.cpp, формат ответа может отличаться
        if "choices" in result and len(result["choices"]) > 0:
            # OpenAI-совместимый формат
            simplified_text = result["choices"][0].get("text", "").strip()
            return simplified_text
        elif "completion" in result:
            # Альтернативный формат
            return result["completion"].strip()
        else:
            print(f"Ошибка: Неизвестный формат ответа LlamaCPP: {result}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"Ошибка: Не удалось подключиться к LlamaCPP по адресу {llamacpp_url}.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к LlamaCPP: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось декодировать ответ от LlamaCPP: {response.text}")
        return None
    except Exception as e:
        print(f"Непредвиденная ошибка при упрощении текста через LlamaCPP: {e}")
        return None

def simplify_with_yandexgpt(text, model="yandexgpt", yandexgpt_url=YANDEXGPT_URL, yandexgpt_api_key=YANDEXGPT_API_KEY, yandexgpt_folder_id=YANDEXGPT_FOLDER_ID):
    """Упрощает текст с помощью YandexGPT API."""
    if not yandexgpt_api_key or not yandexgpt_folder_id:
        print("Ошибка: Не указаны API ключ или идентификатор каталога для YandexGPT")
        return None
        
    prompt = PROMPT_TEMPLATE.replace("{{исходный_абзац}}", text)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {yandexgpt_api_key}",
        "x-folder-id": yandexgpt_folder_id
    }
    
    payload = {
        "modelUri": f"gpt://{yandexgpt_folder_id}/{model}",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "user",
                "text": prompt
            }
        ]
    }
    
    try:
        response = requests.post(yandexgpt_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if "result" in result and "alternatives" in result["result"] and len(result["result"]["alternatives"]) > 0:
            message = result["result"]["alternatives"][0].get("message", {})
            simplified_text = message.get("text", "").strip()
            return simplified_text
        else:
            print(f"Ошибка: Неизвестный формат ответа YandexGPT: {result}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"Ошибка: Не удалось подключиться к YandexGPT")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к YandexGPT: {e}")
        print(f"Ответ: {e.response.text if hasattr(e, 'response') else 'Нет ответа'}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка: Не удалось декодировать ответ от YandexGPT: {response.text}")
        return None
    except Exception as e:
        print(f"Непредвиденная ошибка при упрощении текста через YandexGPT: {e}")
        return None
