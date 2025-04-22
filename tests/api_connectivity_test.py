import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
OLLAMA_API_URL = os.getenv("ollama_api_base") # Changed variable name
LLAMACPP_API_URL = os.getenv("llamacpp_api_base") # Changed variable name
YANDEX_API_KEY = os.getenv("yandexgpt_api_key") # Changed variable name
YANDEX_FOLDER_ID = os.getenv("yandexgpt_folder_id") # Changed variable name
YANDEX_GPT_URL = os.getenv("yandexgpt_url", "https://llm.api.cloud.yandex.net/foundationModels/v1/completion") # Added fallback and correct env var name

# --- Test Functions ---

def test_ollama():
    """Tests connectivity and basic interaction with the Ollama API."""
    print("--- Testing Ollama API ---")
    if not OLLAMA_API_URL:
        print("OLLAMA_API_URL not found in .env. Skipping test.")
        return False

    try:
        # Simple request: list local models (or check API root)
        # Adjust endpoint if needed, e.g., '/api/tags' or just '/'
        test_url = OLLAMA_API_URL.rstrip('/') + '/api/tags'
        print(f"Attempting to connect to Ollama at: {test_url}")
        response = requests.get(test_url, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Check if response is valid JSON (optional, but good practice)
        try:
            models = response.json()
            model_count = len(models.get('models', []))
            print(f"Ollama API responded successfully. Models found: {model_count}")
            
            # Вывод списка моделей
            if model_count > 0:
                print("\nAvailable Ollama models:")
                for i, model in enumerate(models.get('models', []), 1):
                    if isinstance(model, dict) and 'name' in model:
                        # Новый формат Ollama API
                        print(f"  {i}. {model['name']} ({model.get('size', 'unknown size')})")
                    else:
                        # Старый формат Ollama API
                        print(f"  {i}. {model}")
                print()
            
            return True
        except json.JSONDecodeError:
             # Some Ollama endpoints might not return JSON (e.g., just 'Ollama is running')
             print(f"Ollama API responded successfully (Status: {response.status_code}). Response not JSON, but connection OK.")
             return True

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama API: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during Ollama test: {e}")
        return False

def test_llamacpp():
    """Tests connectivity and basic interaction with the LlamaCPP API."""
    print("\n--- Testing LlamaCPP API ---")
    if not LLAMACPP_API_URL:
        print("LLAMACPP_API_URL not found in .env. Skipping test.")
        return False

    try:
        # Simple request: check health or list models
        # Adjust endpoint as needed, e.g., '/health', '/v1/models'
        base_url = LLAMACPP_API_URL.rstrip('/')
        # Ensure we don't double up on '/v1'
        if base_url.endswith('/v1'):
             test_url = base_url + '/models'
        else:
             test_url = base_url + '/v1/models' # Common endpoint for OpenAI compatible servers

        print(f"Attempting to connect to LlamaCPP at: {test_url}")
        response = requests.get(test_url, timeout=10)
        response.raise_for_status()

        # Check if response is valid JSON
        try:
            data = response.json()
            model_count = len(data.get('data', []))
            print(f"LlamaCPP API responded successfully. Models found: {model_count}")
            
            # Вывод списка моделей
            if model_count > 0:
                print("\nAvailable LlamaCPP models:")
                for i, model in enumerate(data.get('data', []), 1):
                    model_id = model.get('id', 'Unknown')
                    owned_by = model.get('owned_by', 'Unknown')
                    created = model.get('created', 'Unknown date')
                    print(f"  {i}. {model_id} (owner: {owned_by}, created: {created})")
                print()
            
            return True
        except json.JSONDecodeError:
             print(f"LlamaCPP API responded successfully (Status: {response.status_code}). Response not JSON, but connection OK.")
             return True # Consider success if connection is okay

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to LlamaCPP API: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during LlamaCPP test: {e}")
        return False

def test_yandexgpt():
    """Tests connectivity and basic interaction with the YandexGPT API."""
    print("\n--- Testing YandexGPT API ---")
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        print("YANDEX_API_KEY or YANDEX_FOLDER_ID not found in .env. Skipping test.")
        return False

    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json",
        "x-folder-id": YANDEX_FOLDER_ID
    }
    
    # Получение списка моделей через OpenAI-совместимый эндпоинт /v1/models
    models_url = "https://llm.api.cloud.yandex.net/v1/models"
    print(f"Requesting available models from: {models_url}")
    models_response = None
    
    try:
        models_response = requests.get(models_url, headers=headers, timeout=15)
        models_response.raise_for_status()
        
        models_result = models_response.json()
        if 'data' in models_result:
            model_count = len(models_result['data'])
            print(f"YandexGPT API responded successfully. Models found: {model_count}")
            
            if model_count > 0:
                print("\nAvailable YandexGPT models:")
                for i, model in enumerate(models_result['data'], 1):
                    model_id = model.get('id', 'Unknown')
                    owned_by = model.get('owned_by', 'Unknown')
                    created = model.get('created', 'Unknown')
                    
                    # Получаем дополнительные параметры, если они есть
                    model_details = []
                    if 'owned_by' in model:
                        model_details.append(f"owner: {owned_by}")
                    if 'created' in model:
                        model_details.append(f"created: {created}")
                        
                    # Выводим модель с деталями
                    details_str = f" ({', '.join(model_details)})" if model_details else ""
                    print(f"  {i}. {model_id}{details_str}")
                print()
        else:
            print("Models list not available in the expected format.")
            print(f"Response body: {json.dumps(models_result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"Could not retrieve models list: {e}")
        if models_response is not None:
            print(f"Response status: {models_response.status_code}")
            try:
                print(f"Response body: {models_response.text}")
            except Exception:
                pass
        print("Continuing with test...")
    
    # Тестирование генерации текста
    # Используем модель, указанную в файле .env или yandexgpt по умолчанию
    model_name = os.getenv("yandexgpt_model", "yandexgpt")
    
    # Исправляем формат model_uri в соответствии с документацией
    # Не используем /latest для совместимости со всеми версиями API
    model_uri = f"gpt://{YANDEX_FOLDER_ID}/{model_name}"
    
    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 50  # Числом, а не строкой
        },
        "messages": [
            {
                "role": "user",
                "text": "Привет! Представься, пожалуйста. Какая ты модель?"
            }
        ]
    }

    response = None
    try:
        print(f"\nTesting completion API at: {YANDEX_GPT_URL}")
        print(f"Using model: {model_uri}")
        response = requests.post(YANDEX_GPT_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()

        # Check response structure
        result = response.json()
        if 'result' in result and 'alternatives' in result['result']:
            alternatives = result['result']['alternatives']
            if alternatives and 'message' in alternatives[0]:
                response_text = alternatives[0]['message'].get('text', '')
                
                # Выводим информацию о запросе
                print("\nModel response test:")
                print(f"  Model URI: {model_uri}")
                print(f"  Model version: {result['result'].get('modelVersion', 'Unknown')}")
                
                # Выводим информацию о токенах
                tokens_used = result['result'].get('tokensUsed', {})
                input_tokens = tokens_used.get('inputTokens', 'Unknown')
                output_tokens = tokens_used.get('outputTokens', 'Unknown')
                total_tokens = tokens_used.get('totalTokens', 'Unknown')
                
                print(f"  Tokens used: {total_tokens} (input: {input_tokens}, output: {output_tokens})")
                
                # Выводим ответ модели (первые 200 символов с многоточием, если ответ длиннее)
                print("\nModel response:")
                if len(response_text) > 200:
                    print(f"{response_text[:200]}...\n")
                else:
                    print(f"{response_text}\n")
                
                return True
            else:
                print("No message text found in response alternatives")
                return False
        else:
            print(f"YandexGPT API responded with unexpected structure")
            print(f"Response body: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to YandexGPT API: {e}")
        if response is not None:
            print(f"Response status: {response.status_code}")
            try:
                print(f"Response body: {response.text}")
            except Exception:
                pass  # Ignore if response body cannot be read
        return False
    except Exception as e:
        print(f"An unexpected error occurred during YandexGPT test: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting API Connectivity Tests...\n")

    results = {
        "Ollama": test_ollama(),
        "LlamaCPP": test_llamacpp(),
        "YandexGPT": test_yandexgpt()
    }

    print("\n--- Test Summary ---")
    all_passed = True
    for api, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"{api}: {status}")
        if not result:
            all_passed = False

    print("\nTest run finished.")
    # Optional: Exit with non-zero status code if any test failed
    # if not all_passed:
    #     import sys
    #     sys.exit(1)
