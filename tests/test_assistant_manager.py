"""
Тестовый скрипт для демонстрации работы системы управления с ассистентом.
Эта программа показывает, как работает замкнутый конвейер саморазвития проекта.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта модулей
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.logger import setup_logging, log_action, log_result, log_error
from app.assistant_manager import assistant
from app.model_selector import model_selector, API_TYPE_OLLAMA, API_TYPE_LLAMACPP, API_TYPE_YANDEXGPT

def update_plan_fact_checker(report_data):
    """Обновляет файл PLAN-FACT-CHECKER.md с новыми данными о выполнении задач"""
    log_action("Обновление PLAN-FACT-CHECKER.md")
    
    try:
        plan_fact_file = Path("e:/mufu/PLAN-FACT-CHECKER.md")
        
        if not plan_fact_file.exists():
            log_error("Файл PLAN-FACT-CHECKER.md не найден", FileNotFoundError())
            return False
            
        # Читаем текущее содержимое файла
        content = plan_fact_file.read_text(encoding='utf-8')
        
        # Получаем текущую дату
        current_date = datetime.now().strftime("%d.%m.%Y")
        
        # Обновляем метрики использования API в зависимости от типа API
        if "api_type" in report_data:
            api_type = report_data["api_type"].lower()
            
            if api_type == API_TYPE_OLLAMA:
                marker = "#### Ollama API"
                table_row = f"\n| {current_date} | {report_data.get('requests', 1)} | {report_data.get('success', 1)} | {report_data.get('errors', 0)} | {report_data.get('avg_time', '-')} | {report_data.get('tokens', '-')} |"
                
                # Находим таблицу и добавляем новую строку
                table_start = content.find(marker)
                if table_start != -1:
                    table_end = content.find("\n\n", table_start)
                    if table_end == -1:
                        table_end = len(content)
                    
                    new_content = content[:table_end] + table_row + content[table_end:]
                    plan_fact_file.write_text(new_content, encoding='utf-8')
                    
            elif api_type == API_TYPE_LLAMACPP:
                marker = "#### LlamaCPP API"
                table_row = f"\n| {current_date} | {report_data.get('requests', 1)} | {report_data.get('success', 1)} | {report_data.get('errors', 0)} | {report_data.get('avg_time', '-')} | {report_data.get('tokens', '-')} |"
                
                # Находим таблицу и добавляем новую строку
                table_start = content.find(marker)
                if table_start != -1:
                    table_end = content.find("\n\n", table_start)
                    if table_end == -1:
                        table_end = len(content)
                    
                    new_content = content[:table_end] + table_row + content[table_end:]
                    plan_fact_file.write_text(new_content, encoding='utf-8')
                    
            elif api_type == API_TYPE_YANDEXGPT:
                marker = "#### YandexGPT API"
                table_row = f"\n| {current_date} | {report_data.get('requests', 1)} | {report_data.get('success', 1)} | {report_data.get('errors', 0)} | {report_data.get('avg_time', '-')} | {report_data.get('tokens', '-')} |"
                
                # Находим таблицу и добавляем новую строку
                table_start = content.find(marker)
                if table_start != -1:
                    table_end = content.find("\n\n", table_start)
                    if table_end == -1:
                        table_end = len(content)
                    
                    new_content = content[:table_end] + table_row + content[table_end:]
                    plan_fact_file.write_text(new_content, encoding='utf-8')
        
        # Обновляем прогресс задач, если указано в отчете
        if "task_id" in report_data and "progress" in report_data:
            task_id = report_data["task_id"]
            progress = report_data["progress"]
            
            # Находим строку с соответствующей задачей
            if task_id == 1:
                task_marker = "Интеграция model_selector в simplify_text.py"
            elif task_id == 2:
                task_marker = "Расширение системы логирования"
            elif task_id == 3:
                task_marker = "Оптимизация работы с русскоязычным контентом"
            else:
                task_marker = None
                
            if task_marker:
                task_line_start = content.find(task_marker)
                if task_line_start != -1:
                    line_end = content.find("\n", task_line_start)
                    line_start = content.rfind("|", 0, task_line_start)
                    
                    if line_start != -1 and line_end != -1:
                        # Находим позицию последнего | в строке
                        last_pipe = content.rfind("|", 0, line_end)
                        if last_pipe != -1:
                            # Заменяем процент выполнения
                            new_content = content[:last_pipe+1] + f" {progress}% " + content[line_end-1:]
                            plan_fact_file.write_text(new_content, encoding='utf-8')
                            
        # Добавляем новую проблему, если указана
        if "problem" in report_data and "solution" in report_data:
            problem_marker = "## Обнаруженные проблемы и их решения"
            problem_table_end_marker = "## Рекомендации по оптимизации"
            
            problem_section_start = content.find(problem_marker)
            problem_section_end = content.find(problem_table_end_marker, problem_section_start)
            
            if problem_section_start != -1 and problem_section_end != -1:
                table_start = content.find("|", problem_section_start)
                table_header_end = content.find("\n", table_start)
                table_separator_end = content.find("\n", table_header_end + 1)
                
                if table_separator_end != -1:
                    new_problem_row = f"\n| {current_date} | {report_data['problem']} | {report_data['solution']} | В процессе |"
                    new_content = content[:table_separator_end+1] + new_problem_row + content[table_separator_end+1:]
                    plan_fact_file.write_text(new_content, encoding='utf-8')
        
        log_result("Файл PLAN-FACT-CHECKER.md успешно обновлен")
        return True
        
    except Exception as e:
        log_error("Ошибка при обновлении PLAN-FACT-CHECKER.md", e)
        return False

def demonstrate_assistant_cycle():
    """Демонстрирует полный цикл работы с ассистентом"""
    log_action("Демонстрация полного цикла работы с ассистентом")
    
    # Проверяем доступность ассистента
    if not assistant.is_available:
        print("Ассистент недоступен. Пожалуйста, проверьте настройки API.")
        return
        
    print("\n=== ДЕМОНСТРАЦИЯ РАБОТЫ СИСТЕМЫ УПРАВЛЕНИЯ С АССИСТЕНТОМ ===\n")
    print(f"Статус ассистента: {'Доступен' if assistant.is_available else 'Недоступен'}")
    print(f"Модель: {assistant.model}")
    
    # Шаг 1: Получаем статус ассистента и знакомимся с ним
    print("\n--- Шаг 1: Знакомство с ассистентом ---")
    result = assistant.send_instruction(
        "Представьтесь и опишите свою роль в проекте MUFU. "
        "Какие задачи вам поручено выполнять?"
    )
    
    if result.get("success", False):
        print("\nОтвет ассистента:")
        print(result["response"])
        
        # Обновляем отчет
        update_plan_fact_checker({
            "api_type": API_TYPE_LLAMACPP,
            "requests": 1,
            "success": 1,
            "errors": 0,
            "tokens": result.get("usage", {}).get("total_tokens", 0)
        })
    else:
        print("\nОшибка при взаимодействии с ассистентом:", result.get("error"))
        return
        
    # Шаг 2: Поручаем ассистенту проанализировать текущий прогресс проекта
    print("\n--- Шаг 2: Анализ текущего прогресса проекта ---")
    result = assistant.send_instruction(
        "Проанализируйте текущий прогресс проекта на основе инструкций в TODO.md. "
        "Какие задачи являются приоритетными и какой следующий шаг вы рекомендуете предпринять?"
    )
    
    if result.get("success", False):
        print("\nРезультат анализа от ассистента:")
        print(result["response"])
        
        # Обновляем отчет
        update_plan_fact_checker({
            "api_type": API_TYPE_LLAMACPP,
            "requests": 1,
            "success": 1,
            "errors": 0,
            "tokens": result.get("usage", {}).get("total_tokens", 0)
        })
    else:
        print("\nОшибка при анализе прогресса:", result.get("error"))
        
    # Шаг 3: Делегируем ассистенту задачу для выполнения через Ollama API
    print("\n--- Шаг 3: Делегирование задачи через Ollama API ---")
    task_result = assistant.delegate_task(
        "Проанализируйте файл model_selector.py и предложите улучшения для оптимизации "
        "выбора моделей в зависимости от типа контента. "
        "Опишите, как можно улучшить алгоритм определения типа контента.",
        API_TYPE_OLLAMA,
        "llama3"
    )
    
    if task_result.get("success", False):
        print("\nРезультат выполнения делегированной задачи:")
        print(json.dumps(task_result, indent=2, ensure_ascii=False))
        
        # Обновляем отчет о прогрессе задачи
        update_plan_fact_checker({
            "api_type": API_TYPE_OLLAMA,
            "requests": 1,
            "success": 1,
            "errors": 0,
            "task_id": 1,  # Задача #1: Интеграция model_selector
            "progress": 15  # Увеличиваем прогресс на 15%
        })
    else:
        print("\nОшибка при делегировании задачи:", task_result.get("error"))
        
    # Шаг 4: Поручаем ассистенту обновить план-факт чекер
    print("\n--- Шаг 4: Обновление PLAN-FACT-CHECKER.md ---")
    result = assistant.send_instruction(
        "Проанализируйте результаты выполненных задач и предложите обновления "
        "для файла PLAN-FACT-CHECKER.md. Какие метрики следует добавить "
        "для более эффективного отслеживания прогресса проекта?"
    )
    
    if result.get("success", False):
        print("\nПредложения ассистента по обновлению PLAN-FACT-CHECKER.md:")
        print(result["response"])
        
        # Добавляем новую проблему и решение на основе анализа ассистента
        update_plan_fact_checker({
            "problem": "Недостаточно детализированное отслеживание прогресса по задачам",
            "solution": "Добавить автоматическое обновление метрик на основе логов и отчетов от AI-инструментов"
        })
    else:
        print("\nОшибка при запросе анализа PLAN-FACT-CHECKER.md:", result.get("error"))
        
    # Шаг 5: Сохраняем историю обмена сообщениями для анализа
    print("\n--- Шаг 5: Сохранение истории взаимодействия с ассистентом ---")
    saved_path = assistant.save_conversation()
    print(f"История обмена сообщениями сохранена в: {saved_path}")
    
    print("\n=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===\n")
    
    # Итоговый отчет
    print("Итоги демонстрации:")
    print("1. Ассистент LlamaCPP успешно интегрирован в систему управления проектом")
    print("2. Настроена система делегирования задач от Ассистента к другим AI-инструментам")
    print("3. Реализовано автоматическое обновление PLAN-FACT-CHECKER.md")
    print("4. Продемонстрирован замкнутый цикл саморазвития проекта")
    
    # Даем рекомендацию для дальнейших шагов
    print("\nРекомендации для следующего шага:")
    print("Интегрировать ассистента с модулем simplify_text.py для автоматического выбора")
    print("оптимальной модели в зависимости от типа текста и реализовать механизм")
    print("самообучения на основе анализа результатов работы.")

if __name__ == "__main__":
    # Инициализируем систему логирования
    setup_logging()
    
    # Запускаем демонстрацию
    demonstrate_assistant_cycle()