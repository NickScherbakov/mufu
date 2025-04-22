"""
Тестирование ассистента с использованием API LlamaCPP.
Этот скрипт задает вопросы из файла test_assistant_questions.md
ассистенту через LlamaCPP API и сохраняет результаты.
"""
import os
import sys

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
import re
import time
from datetime import datetime
from pathlib import Path
from app.utils import get_env
from app.logger import setup_logging, log_action, log_result, log_error

def extract_questions_from_md(md_file_path):
    """
    Извлекает вопросы из markdown файла.
    Возвращает словарь с категориями вопросов.
    """
    if not os.path.exists(md_file_path):
        log_error(f"Файл с вопросами не найден: {md_file_path}")
        return {}
    
    with open(md_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Ищем заголовки категорий (## ...) и вопросы (цифры с точкой)
    categories = {}
    current_category = "Общие вопросы"
    
    # Разбиваем файл на строки для анализа
    lines = content.split('\n')
    for line in lines:
        # Проверяем, не является ли строка заголовком категории
        if line.startswith('## '):
            current_category = line[3:].strip()
            categories[current_category] = []
        
        # Ищем вопросы (строки с цифрой, точкой и кавычками)
        question_match = re.search(r'\d+\.\s+\*\*[^*]+\*\*\s*:\s*"([^"]+)"', line)
        if question_match:
            question = question_match.group(1).strip()
            if current_category not in categories:
                categories[current_category] = []
            categories[current_category].append(question)
    
    return categories

def ask_llamacpp(question, llamacpp_url, llamacpp_api_key=None, system_prompt=None):
    """
    Отправляет вопрос к LlamaCPP API и получает ответ.
    """
    headers = {"Content-Type": "application/json"}
    if llamacpp_api_key and llamacpp_api_key != "NA":
        headers["Authorization"] = f"Bearer {llamacpp_api_key}"
    
    chat_url = f"{llamacpp_url.rstrip('/')}/chat/completions"
    
    messages = []
    # Добавляем системный промпт, если он предоставлен
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Добавляем вопрос пользователя
    messages.append({"role": "user", "content": question})
    
    payload = {
        "model": "default",  # Используем модель по умолчанию
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(chat_url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # Обработка ответа в формате OpenAI API
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0]:
                return result["choices"][0]["message"].get("content", "")
            return result["choices"][0].get("text", "")
        
        # Альтернативный формат
        return result.get("response", str(result))
        
    except Exception as e:
        log_error(f"Ошибка при отправке запроса к API: {e}")
        return f"ОШИБКА: {str(e)}"

def run_assistant_test():
    """
    Запускает тестирование ассистента с вопросами из файла.
    """
    print("Тестирование ассистента с использованием LlamaCPP API...")
    
    # Получаем URL и API ключ из .env
    llamacpp_url = get_env("llamacpp_api_base", "http://localhost:8080/v1")
    llamacpp_api_key = get_env("llamacpp_api_key", "NA")
    
    # Проверяем, что URL задан
    if not llamacpp_url:
        print("ОШИБКА: URL для LlamaCPP API не найден в .env файле!")
        return False
    
    print(f"Используемый URL LlamaCPP API: {llamacpp_url}")
    
    # Проверяем доступность API
    try:
        api_models_url = f"{llamacpp_url.rstrip('/')}/models"
        headers = {}
        if llamacpp_api_key and llamacpp_api_key != "NA":
            headers["Authorization"] = f"Bearer {llamacpp_api_key}"
        
        response = requests.get(api_models_url, headers=headers)
        response.raise_for_status()
        print("LlamaCPP API доступен.")
    except Exception as e:
        print(f"ОШИБКА: Не удалось подключиться к LlamaCPP API: {e}")
        return False
    
    # Путь к файлу с вопросами
    questions_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_assistant_questions.md')
    
    # Получаем вопросы из файла
    categories = extract_questions_from_md(questions_file)
    
    if not categories:
        print("ОШИБКА: Не удалось извлечь вопросы из файла!")
        return False
    
    # Формируем системный промпт для ассистента
    system_prompt = """
    Ты - ассистент для создания образовательного видеоконтента.
    Твоя задача - помогать с генерацией сценариев, озвучиванием текста,
    созданием изображений и объединением всего в видеоролик.
    Отвечай на вопросы четко и информативно, предлагая конкретные решения.
    """
    
    # Создаем директорию для результатов, если её нет
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs', 'assistant_test_results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Формируем имя файла для результатов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"assistant_test_results_{timestamp}.md")
    
    total_questions = sum(len(questions) for questions in categories.values())
    processed_questions = 0
    
    # Открываем файл для записи результатов
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write(f"# Результаты тестирования ассистента через LlamaCPP API\n")
        f.write(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Проходим по каждой категории вопросов
        for category, questions in categories.items():
            f.write(f"## {category}\n\n")
            
            for i, question in enumerate(questions, 1):
                processed_questions += 1
                print(f"Обработка вопроса {processed_questions}/{total_questions}: {question[:50]}...")
                
                # Задаем вопрос API
                answer = ask_llamacpp(question, llamacpp_url, llamacpp_api_key, system_prompt)
                
                # Записываем результат в файл
                f.write(f"### Вопрос {i}: {question}\n\n")
                f.write(f"**Ответ:**\n\n{answer}\n\n")
                f.write("---\n\n")
                
                # Небольшая пауза, чтобы не перегружать API
                time.sleep(1)
    
    print(f"\nТестирование завершено. Результаты сохранены в файл: {results_file}")
    return True

if __name__ == "__main__":
    print("Тестирование ассистента с вопросами через LlamaCPP API")
    print("=" * 80)
    
    # Инициализируем логирование
    setup_logging()
    log_action("Запуск тестирования ассистента через LlamaCPP API")
    
    success = run_assistant_test()
    
    if success:
        log_result("Тестирование ассистента успешно завершено")
        print("\nТЕСТ ЗАВЕРШЕН: Проверка ассистента через LlamaCPP API выполнена успешно!")
        sys.exit(0)
    else:
        log_error("Возникли проблемы при тестировании ассистента")
        print("\nТЕСТ НЕ ЗАВЕРШЕН: Возникли проблемы при тестировании ассистента.")
        sys.exit(1)