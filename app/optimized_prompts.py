"""
Оптимизированные промпты для API llama.cpp.
Этот модуль содержит готовые промпты для различных задач,
которые были протестированы и оптимизированы для предотвращения
зацикливаний и других проблем взаимодействия с API LlamaCPP.
"""
import json
from typing import Dict, List, Optional, Any

# Базовые системные промпты
REASONING_SYSTEM_PROMPT = (
    "Ты - логический ассистент, который помогает решать задачи с помощью структурированного мышления. "
    "Используй пошаговый подход и логические рассуждения для нахождения решения. "
    "Избегай повторений и будь конкретным. В конце обязательно сформулируй итоговый ответ."
)

STRUCTURED_SYSTEM_PROMPT = (
    "Ты - технический эксперт, который объясняет сложные концепции пошагово. "
    "Твои объяснения должны быть структурированы, ясны и включать примеры. "
    "После объяснения обобщи ключевые моменты."
)

# Улучшенные промпты для конкретных задач
def get_sorting_algorithm_prompt(algorithm_name: str, array: List[int]) -> Dict[str, Any]:
    """
    Создает оптимизированный промпт для объяснения алгоритма сортировки.
    
    Args:
        algorithm_name: Название алгоритма сортировки (например, "merge sort")
        array: Массив для демонстрации работы алгоритма
        
    Returns:
        Dict[str, Any]: Структура запроса для API
    """
    array_str = str(array)
    
    # Промпт с четкой структурой и ограничениями для предотвращения зацикливания
    user_content = f"""Объясни алгоритм сортировки {algorithm_name} в следующем формате:

1. КОНЦЕПЦИЯ: Краткое описание принципа работы алгоритма (2-3 предложения)
2. СЛОЖНОСТЬ: Временная и пространственная сложность алгоритма
3. АЛГОРИТМ: Структурированное описание шагов алгоритма
4. ПРАКТИЧЕСКИЙ ПРИМЕР: Пошаговый пример работы на массиве {array_str}
5. ЗАКЛЮЧЕНИЕ: Краткий вывод о преимуществах и недостатках алгоритма

Важно: каждый шаг примера должен показывать конкретное состояние массива.
"""
    
    system_content = (
        "Ты - опытный преподаватель алгоритмов, объясняющий сложные концепции простым языком. "
        "Отвечай кратко, точно и избегай повторений. Следуй строго запрошенной структуре."
    )
    
    return {
        "model": "default",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.1,  # Низкая температура для более детерминированных ответов
        "top_p": 0.9,
        "max_tokens": 2048,
        "stop": ["КОНЕЦ.", "Удачи!", "Надеюсь", "P.S."]  # Стоп-слова для предотвращения дополнительного ненужного текста
    }

def get_logical_puzzle_prompt(puzzle_text: str) -> Dict[str, Any]:
    """
    Создает оптимизированный промпт для решения логической задачи.
    
    Args:
        puzzle_text: Текст логической задачи
        
    Returns:
        Dict[str, Any]: Структура запроса для API
    """
    user_content = f"""Реши следующую логическую задачу пошагово:

{puzzle_text}

Формат решения:
1. АНАЛИЗ УСЛОВИЙ: Выпиши все условия задачи в виде отдельных фактов
2. РАССУЖДЕНИЕ: Проведи пошаговое рассуждение, делая логические выводы из имеющихся фактов
3. ОТВЕТ: Сформулируй четкий финальный ответ
"""
    
    return {
        "model": "default",
        "messages": [
            {"role": "system", "content": REASONING_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 1024
    }

def get_function_call_prompt(question: str, functions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Создает оптимизированный промпт для вызова функций.
    
    Args:
        question: Вопрос пользователя
        functions: Список доступных функций
        
    Returns:
        Dict[str, Any]: Структура запроса для API
    """
    system_content = (
        "Ты - ассистент, который помогает пользователям получать информацию. "
        "Используй предоставленные функции для выполнения запросов. "
        "Не пытайся самостоятельно придумывать данные, которые должны быть получены через функции."
    )
    
    return {
        "model": "default",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question}
        ],
        "functions": functions,
        "temperature": 0.0,  # Минимальная температура для точных функциональных вызовов
        "response_format": {"type": "json_object"}  # Ожидаем структурированный JSON
    }

# Оптимизированный запрос для тестирования алгоритма сортировки слиянием
MERGE_SORT_PROMPT = get_sorting_algorithm_prompt("сортировки слиянием (merge sort)", [8, 3, 5, 1, 9, 2])

# Запрос для тестирования решения логической задачи (используется в test_reasoning_api.py)
LOGICAL_PUZZLE_PROMPT = get_logical_puzzle_prompt(
    """У Ани, Бори и Вовы есть любимые цвета: красный, синий и зеленый. Известно, что:
1. Аня не любит красный цвет
2. У Бори не синий любимый цвет
3. Вова дружит с тем, у кого любимый цвет - зеленый
4. Тот, кто любит красный цвет, не дружит с Аней

Определи, какой любимый цвет у каждого из ребят."""
)

# Запрос для тестирования функциональных вызовов
WEATHER_FUNCTION = [
    {
        "name": "get_weather",
        "description": "Получает информацию о погоде для указанного города",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Название города для получения погоды"
                },
                "date": {
                    "type": "string",
                    "description": "Дата, для которой нужна погода (сегодня, завтра, etc)"
                }
            },
            "required": ["city"]
        }
    }
]

WEATHER_FUNCTION_PROMPT = get_function_call_prompt(
    "Какая погода будет завтра в Москве?",
    WEATHER_FUNCTION
)