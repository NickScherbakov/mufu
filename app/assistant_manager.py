"""
Assistant Manager модуль для координации взаимодействия между главным координатором и его ассистентом.
Использует LlamaCPP API в качестве ассистента для управления другими AI-инструментами.
Включает поддержку межвидового взаимодействия и различных форм разума.
"""

import os
import json
import requests
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, Generator

# Добавляем родительскую директорию в путь поиска модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.logger import log_action, log_result, log_error, log_decision
from app.utils import get_env
from app.model_selector import model_selector, API_TYPE_LLAMACPP

# Увеличенное время ожидания для больших моделей (в секундах)
DEFAULT_TIMEOUT = 300  # 5 минут вместо 3 минут
# Размер чанка для потоковой обработки (в символах)
DEFAULT_STREAM_CHUNK_SIZE = 4  # По умолчанию llama.cpp отправляет по 4 символа
# Задержка между запросами (в секундах)
REQUEST_DELAY = 0.5  # Добавляем небольшую задержку между запросами для стабильности

# Параметры для reasoning моделей
REASONING_TEMPERATURE = 0.1  # Низкая температура для более логичных рассуждений
REASONING_TOP_P = 0.9  # Ограничение вероятности для более предсказуемых результатов
REASONING_MAX_TOKENS = 4096  # Максимальное количество токенов для генерации рассуждений

# Параметры для функциональных вызовов
FUNCTION_CALLING_TEMPERATURE = 0.0  # Минимальная температура для точных функциональных вызовов
FUNCTION_JSON_SCHEMA = {"type": "json_object"}  # Стандартная JSON схема для ответов

# Добавляем константы для типов форм разума
INTELLIGENCE_TYPE_HUMAN = "human"
INTELLIGENCE_TYPE_AI = "ai"
INTELLIGENCE_TYPE_ANIMAL = "animal"
INTELLIGENCE_TYPE_COLLECTIVE = "collective"
INTELLIGENCE_TYPE_EXTRATERrestrial = "extraterrestrial"

class MultiIntelligenceAdapter:
    """
    Адаптер для взаимодействия с различными формами разума.
    Преобразует сообщения и контент для оптимального восприятия конкретной формой разума.
    """
    
    def __init__(self):
        """Инициализация адаптера."""
        self.adapters = {
            INTELLIGENCE_TYPE_HUMAN: self._adapt_for_human,
            INTELLIGENCE_TYPE_AI: self._adapt_for_ai,
            INTELLIGENCE_TYPE_ANIMAL: self._adapt_for_animal,
            INTELLIGENCE_TYPE_COLLECTIVE: self._adapt_for_collective,
            INTELLIGENCE_TYPE_EXTRATERrestrial: self._adapt_for_extraterrestrial
        }
        
        # Словарь характеристик различных форм разума для лучшей адаптации контента
        self.intelligence_profiles = {
            INTELLIGENCE_TYPE_HUMAN: {
                "text_complexity": 0.8,  # От 0 до 1, где 1 - максимальная сложность
                "visual_dependency": 0.7,  # Насколько важны визуальные элементы
                "auditory_dependency": 0.6,  # Насколько важны аудио элементы
                "preferred_structure": "narrative",  # Нарративная структура изложения
                "attention_span": 0.6,  # Средняя концентрация внимания
                "abstraction_capability": 0.8  # Способность к абстрактному мышлению
            },
            INTELLIGENCE_TYPE_AI: {
                "text_complexity": 1.0,
                "visual_dependency": 0.3,
                "auditory_dependency": 0.2,
                "preferred_structure": "structured",
                "attention_span": 1.0,
                "abstraction_capability": 1.0
            },
            INTELLIGENCE_TYPE_ANIMAL: {
                "text_complexity": 0.2,
                "visual_dependency": 0.9,
                "auditory_dependency": 0.9,
                "preferred_structure": "associative",
                "attention_span": 0.3,
                "abstraction_capability": 0.4
            },
            INTELLIGENCE_TYPE_COLLECTIVE: {
                "text_complexity": 0.9,
                "visual_dependency": 0.5,
                "auditory_dependency": 0.5,
                "preferred_structure": "multi-layered",
                "attention_span": 0.8,
                "abstraction_capability": 0.9
            },
            INTELLIGENCE_TYPE_EXTRATERrestrial: {
                "text_complexity": 0.8,  # Предполагаемое значение
                "visual_dependency": 0.7,  # Предполагаемое значение
                "auditory_dependency": 0.7,  # Предполагаемое значение
                "preferred_structure": "unknown",  # Требует дополнительного изучения
                "attention_span": 0.8,  # Предполагаемое значение
                "abstraction_capability": 0.9  # Предполагаемое значение
            }
        }
        
        log_action("Инициализирован адаптер для межвидового взаимодействия")
    
    def adapt_message(self, message: str, intelligence_type: str, 
                      custom_profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Адаптирует сообщение для конкретной формы разума.
        
        Args:
            message: Исходное сообщение
            intelligence_type: Тип формы разума (human, ai, animal, collective, extraterrestrial)
            custom_profile: Пользовательский профиль формы разума (если нужна особая адаптация)
            
        Returns:
            str: Адаптированное сообщение
        """
        log_action(f"Адаптация сообщения для формы разума: {intelligence_type}")
        
        if intelligence_type in self.adapters:
            adapted_message = self.adapters[intelligence_type](message, custom_profile)
            log_result(f"Сообщение адаптировано для {intelligence_type}")
            return adapted_message
        else:
            log_error(f"Неизвестный тип разума: {intelligence_type}", 
                     ValueError(f"Неподдерживаемый тип разума: {intelligence_type}"))
            return message
    
    def _adapt_for_human(self, message: str, custom_profile: Optional[Dict[str, Any]] = None) -> str:
        """Адаптирует сообщение для человеческого разума."""
        profile = custom_profile or self.intelligence_profiles[INTELLIGENCE_TYPE_HUMAN]
        
        # Для людей важно сохранить структуру текста и добавить визуальные маркеры
        adapted = message
        
        # Если сложность текста высока, добавляем вспомогательные пояснения
        if profile["text_complexity"] < 0.7 and len(message) > 200:
            lines = message.split('\n')
            adapted = "Краткое содержание: " + self._summarize(message) + "\n\n" + "\n".join(lines)
            
        return adapted
    
    def _adapt_for_ai(self, message: str, custom_profile: Optional[Dict[str, Any]] = None) -> str:
        """Адаптирует сообщение для искусственного интеллекта."""
        # Для AI важны четкие структуры данных и формализованное представление
        profile = custom_profile or self.intelligence_profiles[INTELLIGENCE_TYPE_AI]
        
        # Для AI можем добавить метаинформацию и структурировать данные
        # Например, добавить JSON-структуру или форматирование markdown
        if not message.startswith("```") and len(message) > 100:
            adapted = f"""```meta
type: instruction
timestamp: {datetime.now().isoformat()}
complexity: {self._calculate_text_complexity(message)}
```

{message}

```decision_points
1. Определите приоритетность задачи
2. Оцените необходимые ресурсы
3. Сформируйте план действий
```"""
        else:
            adapted = message
            
        return adapted
    
    def _adapt_for_animal(self, message: str, custom_profile: Optional[Dict[str, Any]] = None) -> str:
        """Адаптирует сообщение для животного разума."""
        profile = custom_profile or self.intelligence_profiles[INTELLIGENCE_TYPE_ANIMAL]
        
        # Для животных упрощаем сообщение до базовых концепций и ассоциаций
        # Используем короткие предложения, повторы, эмоциональные маркеры
        words = message.split()
        if len(words) > 20:
            # Выбираем ключевые слова и создаем упрощенные ассоциативные конструкции
            key_words = self._extract_key_terms(message, 5)
            associations = " - ".join(key_words)
            adapted = f"КЛЮЧЕВЫЕ АССОЦИАЦИИ: {associations}\n\nУПРОЩЕННОЕ СООБЩЕНИЕ:\n"
            
            # Создаем упрощенную версию
            simple_sentences = []
            current_sentence = []
            
            for word in words[:100]:  # Ограничиваем длину
                current_sentence.append(word)
                if len(current_sentence) >= 5 or word.endswith(('.', '!', '?')):
                    simple_sentences.append(' '.join(current_sentence))
                    current_sentence = []
            
            if current_sentence:
                simple_sentences.append(' '.join(current_sentence))
                
            adapted += '\n'.join(simple_sentences)
        else:
            adapted = message
            
        return adapted
    
    def _adapt_for_collective(self, message: str, custom_profile: Optional[Dict[str, Any]] = None) -> str:
        """Адаптирует сообщение для коллективного разума."""
        profile = custom_profile or self.intelligence_profiles[INTELLIGENCE_TYPE_COLLECTIVE]
        
        # Для коллективного разума важна многоуровневая структура с разными слоями информации
        # Добавляем метки для разных уровней восприятия
        adapted = message
        
        if len(message) > 300:
            sections = message.split('\n\n')
            adapted = f"## МНОГОУРОВНЕВОЕ СООБЩЕНИЕ ДЛЯ КОЛЛЕКТИВНОГО РАЗУМА ##\n\n"
            
            # Уровень 1: Общая суть (для высокоуровневого восприятия)
            adapted += f"### УРОВЕНЬ 1: ОБЩАЯ КОНЦЕПЦИЯ ###\n"
            adapted += self._summarize(message) + "\n\n"
            
            # Уровень 2: Структурированная информация (для аналитического восприятия)
            adapted += f"### УРОВЕНЬ 2: СТРУКТУРИРОВАННАЯ ИНФОРМАЦИЯ ###\n"
            for i, section in enumerate(sections[:min(5, len(sections))]):
                adapted += f"РАЗДЕЛ {i+1}: {section.strip()}\n\n"
                
            # Уровень 3: Детали и нюансы (для углубленного анализа)
            adapted += f"### УРОВЕНЬ 3: ДЕТАЛИ И КОНТЕКСТ ###\n"
            adapted += message
        
        return adapted
    
    def _adapt_for_extraterrestrial(self, message: str, custom_profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Адаптирует сообщение для внеземного разума.
        Используем универсальные концепции и мультимодальный подход.
        """
        profile = custom_profile or self.intelligence_profiles[INTELLIGENCE_TYPE_EXTRATERrestrial]
        
        # Для внеземных форм разума предполагаем универсальные методы коммуникации:
        # математика, физика, визуальные образы, логические конструкции
        adapted = f"""
МЕЖВИДОВОЕ СООБЩЕНИЕ [МЕЖЗВЕЗДНЫЙ ПРОТОКОЛ КОММУНИКАЦИИ]

УНИВЕРСАЛЬНЫЙ РАЗДЕЛ:
{self._create_universal_concepts(message)}

СЕМАНТИЧЕСКИЙ РАЗДЕЛ:
{message}

ЛОГИКО-МАТЕМАТИЧЕСКИЙ РАЗДЕЛ:
{self._extract_logical_structure(message)}

ПРИМЕЧАНИЕ: Это сообщение создано с учетом потенциальных различий в когнитивных моделях и восприятии.
"""
        return adapted
    
    def _summarize(self, text: str) -> str:
        """Создает простое резюме текста."""
        words = text.split()
        if len(words) <= 20:
            return text
            
        # Простая эвристика для выделения важных предложений
        sentences = text.replace('\n', ' ').split('. ')
        if len(sentences) <= 3:
            return '. '.join(sentences)
            
        # Берем первое предложение и одно-два из середины
        summary = sentences[0]
        if len(sentences) > 5:
            middle_idx = len(sentences) // 2
            summary += ". " + sentences[middle_idx]
            
        return summary + "."
    
    def _extract_key_terms(self, text: str, count: int = 5) -> List[str]:
        """Извлекает ключевые термы из текста."""
        # Очень простая эвристика - берем самые длинные слова
        words = [word.strip('.,!?:;()[]{}"\'-') for word in text.split()]
        unique_words = list(set(words))
        unique_words.sort(key=lambda x: len(x), reverse=True)
        return unique_words[:count]
    
    def _calculate_text_complexity(self, text: str) -> float:
        """Рассчитывает приблизительную сложность текста."""
        words = text.split()
        avg_word_len = sum(len(word) for word in words) / max(1, len(words))
        sentences = text.replace('\n', ' ').split('. ')
        avg_sentence_len = sum(len(sentence.split()) for sentence in sentences) / max(1, len(sentences))
        
        # Нормализация до 0-1
        complexity = min(1.0, (avg_word_len / 10) * 0.5 + (avg_sentence_len / 20) * 0.5)
        return round(complexity, 2)
    
    def _create_universal_concepts(self, text: str) -> str:
        """Создает универсальные концепции на основе текста."""
        # Здесь можно было бы реализовать извлечение математических или физических концепций
        # Для демонстрации используем простой подход
        return "Данное сообщение содержит информацию о межразумном взаимодействии и адаптации контента."
    
    def _extract_logical_structure(self, text: str) -> str:
        """Извлекает логическую структуру сообщения."""
        # Упрощенная версия для демонстрации
        parts = text.split('\n\n')
        structure = []
        
        for i, part in enumerate(parts):
            if part:
                structure.append(f"Логический блок {i+1}: {part[:30]}...")
                
        return "\n".join(structure)

class AssistantManager:
    """
    Класс для управления ассистентом на базе LlamaCPP API.
    Обеспечивает взаимодействие между главным координатором и его ассистентом,
    а также делегирование задач другим AI-инструментам.
    """
    
    def __init__(self):
        """Инициализирует менеджера ассистента с настройками из .env."""
        self.api_base = get_env("llamacpp_api_base", "http://localhost:8080/v1")
        self.api_key = get_env("llamacpp_api_key", "NA")
        self.model = get_env("llamacpp_default_model", "")
        
        # Метаданные ассистента
        self.assistant_name = "LlamaCPP Assistant"
        self.assistant_role = "Ассистент главного координатора проекта"
        self.assistant_created_at = datetime.now()
        
        # Флаг доступности ассистента
        self.is_available = False
        self._check_availability()
        
        # Инструкции для ассистента
        self.instructions_file = Path("e:/mufu/TODO.md")
        self.instructions = self._load_instructions()
        
        # Журнал обмена сообщениями с ассистентом
        self.message_history = []
        
        # Инициализация адаптера для межвидового взаимодействия
        self.intelligence_adapter = MultiIntelligenceAdapter()
        
        # Текущий тип разума для взаимодействия
        self.current_intelligence_type = INTELLIGENCE_TYPE_HUMAN
    
    def _check_availability(self) -> bool:
        """
        Проверяет доступность API ассистента.
        
        Returns:
            bool: True, если API доступен
        """
        log_action("Проверка доступности API ассистента (LlamaCPP)")
        
        try:
            # Проверка доступности API ассистента через эндпоинт /models
            url = f"{self.api_base.rstrip('/')}/models"
            headers = {}
            if self.api_key and self.api_key != "NA":
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = requests.get(url, headers=headers, timeout=5)
            self.is_available = response.status_code == 200
            
            # Если API доступен, получаем информацию о модели
            if self.is_available и "data" in response.json():
                models = response.json()["data"]
                # Обновляем имя модели из списка доступных, если оно не задано
                if not self.model and models:
                    self.model = models[0].get("id", "")
                    log_decision(f"Автоматический выбор модели: {self.model}")
            
            if self.is_available:
                log_result(f"API ассистента доступен, используется модель: {self.model}")
            else:
                log_error("API ассистента недоступен", 
                          Exception(f"HTTP статус: {response.status_code}"))
                
            return self.is_available
            
        except requests.exceptions.Timeout:
            log_error("Ошибка таймаута при проверке доступности API ассистента", Exception("Timeout"))
            self.is_available = False
            return False
        except Exception as e:
            log_error("Ошибка при проверке доступности API ассистента", e)
            self.is_available = False
            return False
            
    def _load_instructions(self) -> str:
        """
        Загружает инструкции для ассистента из файла TODO.md.
        
        Returns:
            str: Текст инструкций
        """
        log_action("Загрузка инструкций для ассистента")
        
        try:
            if self.instructions_file.exists():
                instructions = self.instructions_file.read_text(encoding='utf-8')
                log_result(f"Инструкции загружены, размер: {len(instructions)} символов")
                return instructions
            else:
                default_instructions = "Вы ассистент главного координатора проекта MUFU."
                log_error("Файл инструкций не найден, используются стандартные инструкции", 
                          FileNotFoundError(f"Файл {self.instructions_file} не существует"))
                return default_instructions
                
        except Exception as e:
            log_error("Ошибка при загрузке инструкций", e)
            return "Вы ассистент главного координатора проекта MUFU."
    
    def send_instruction(self, instruction: str, intelligence_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Отправляет инструкцию ассистенту, адаптируя её для конкретной формы разума.
        
        Args:
            instruction: Текст инструкции или задания для ассистента
            intelligence_type: Тип формы разума (по умолчанию - текущий тип)
            
        Returns:
            Dict[str, Any]: Ответ ассистента или информация об ошибке
        """
        if not intelligence_type:
            intelligence_type = self.current_intelligence_type
            
        if not self.is_available:
            self._check_availability()
            
        if not self.is_available:
            error_msg = "Ассистент недоступен, невозможно отправить инструкцию"
            log_error(error_msg, Exception("API недоступен"))
            return {"error": error_msg, "success": False}
        
        log_action(f"Отправка инструкции ассистенту от {intelligence_type}: {instruction[:50]}...")
        
        try:
            # Адаптируем инструкцию для формы разума
            adapted_instruction = instruction
            if intelligence_type != INTELLIGENCE_TYPE_HUMAN:
                # Только для не-человеческих форм разума применяем адаптацию
                adapted_instruction = self.intelligence_adapter.adapt_message(
                    instruction, INTELLIGENCE_TYPE_AI
                )
            
            # Формируем контекст сообщения
            system_prompt = f"""Вы ассистент главного координатора проекта MUFU.
            
{self.instructions}

Текущая дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
Вы должны помогать выполнять инструкции главного координатора и управлять другими AI-инструментами.
Отвечайте точно и по делу, предлагайте конкретные решения.

Текущий собеседник: {intelligence_type}. Адаптируйте свой ответ для данной формы разума."""

            # Сохраняем историю для контекста
            if not self.message_history:
                self.message_history.append({
                    "role": "system",
                    "content": system_prompt
                })
                
            # Добавляем новое сообщение от пользователя
            self.message_history.append({
                "role": "user",
                "content": adapted_instruction
            })
            
            # Отправляем запрос к API
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key and self.api_key != "NA":
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            payload = {
                "model": self.model,
                "messages": self.message_history,
                "temperature": 0.3,  # Низкая температура для более детерминированных ответов
                "stream": False
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    assistant_message = result["choices"][0]["message"]
                    
                    # Адаптируем ответ ассистента для указанной формы разума
                    adapted_response = assistant_message.get("content", "")
                    if intelligence_type != INTELLIGENCE_TYPE_AI:
                        adapted_response = self.intelligence_adapter.adapt_message(
                            adapted_response, intelligence_type
                        )
                    
                    # Добавляем ответ ассистента в историю (неадаптированный для сохранения контекста)
                    self.message_history.append({
                        "role": assistant_message.get("role", "assistant"),
                        "content": assistant_message.get("content", "")
                    })
                    
                    # Ограничиваем длину истории до 20 сообщений
                    if len(self.message_history) > 20:
                        # Оставляем системное сообщение и последние 19
                        self.message_history = [self.message_history[0]] + self.message_history[-19:]
                    
                    log_result(f"Получен ответ от ассистента (адаптирован для {intelligence_type})", {
                        "length": len(adapted_response),
                        "tokens": result.get("usage", {}).get("total_tokens", 0)
                    })
                    
                    return {
                        "success": True,
                        "response": adapted_response,
                        "original_response": assistant_message.get("content", ""),
                        "intelligence_type": intelligence_type,
                        "usage": result.get("usage", {})
                    }
                else:
                    error_msg = "Некорректный формат ответа от API"
                    log_error(error_msg, Exception("Отсутствует поле choices в ответе"))
                    return {"error": error_msg, "success": False}
            else:
                error_msg = f"Ошибка при отправке запроса к API: {response.status_code}"
                log_error(error_msg, Exception(response.text))
                return {"error": error_msg, "success": False, "status_code": response.status_code}
                
        except requests.exceptions.Timeout:
            error_msg = "Ошибка таймаута при отправке запроса к API"
            log_error(error_msg, Exception("Timeout"))
            return {"error": error_msg, "success": False}
        except Exception as e:
            log_error("Неожиданная ошибка при взаимодействии с ассистентом", e)
            return {"error": str(e), "success": False}
    
    def set_intelligence_type(self, intelligence_type: str) -> bool:
        """
        Устанавливает текущий тип разума для взаимодействия.
        
        Args:
            intelligence_type: Тип формы разума
            
        Returns:
            bool: True, если тип успешно установлен
        """
        if intelligence_type in [INTELLIGENCE_TYPE_HUMAN, INTELLIGENCE_TYPE_AI, 
                               INTELLIGENCE_TYPE_ANIMAL, INTELLIGENCE_TYPE_COLLECTIVE, 
                               INTELLIGENCE_TYPE_EXTRATERrestrial]:
            self.current_intelligence_type = intelligence_type
            log_result(f"Установлен новый тип разума для взаимодействия: {intelligence_type}")
            return True
        else:
            log_error(f"Неподдерживаемый тип разума: {intelligence_type}", ValueError())
            return False

    def get_intelligence_types(self) -> List[str]:
        """
        Возвращает список поддерживаемых типов разума.
        
        Returns:
            List[str]: Список поддерживаемых типов разума
        """
        return [
            INTELLIGENCE_TYPE_HUMAN,
            INTELLIGENCE_TYPE_AI,
            INTELLIGENCE_TYPE_ANIMAL,
            INTELLIGENCE_TYPE_COLLECTIVE,
            INTELLIGENCE_TYPE_EXTRATERrestrial
        ]
    
    def get_intelligence_profile(self, intelligence_type: str) -> Dict[str, Any]:
        """
        Возвращает профиль для указанного типа разума.
        
        Args:
            intelligence_type: Тип формы разума
            
        Returns:
            Dict[str, Any]: Профиль с характеристиками типа разума
        """
        if intelligence_type in self.intelligence_adapter.intelligence_profiles:
            return self.intelligence_adapter.intelligence_profiles[intelligence_type]
        else:
            return {}
    
    def delegate_task(self, task: str, api_type: str, model_name: Optional[str] = None, 
                     intelligence_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Делегирует задачу другому AI-инструменту через ассистента с учетом формы разума.
        
        Args:
            task: Текст задания для выполнения
            api_type: Тип API (ollama, llamacpp, yandexgpt)
            model_name: Название модели (опционально)
            intelligence_type: Тип формы разума (по умолчанию - текущий тип)
            
        Returns:
            Dict[str, Any]: Результат выполнения задачи
        """
        if not intelligence_type:
            intelligence_type = self.current_intelligence_type
            
        log_action(f"Делегирование задачи через ассистента в {api_type} для {intelligence_type}")
        
        # Адаптируем задачу для указанного типа разума
        adapted_task = task
        if intelligence_type != INTELLIGENCE_TYPE_HUMAN:
            adapted_task = self.intelligence_adapter.adapt_message(task, intelligence_type)
        
        delegation_instruction = f"""
Делегируйте выполнение следующей задачи AI-инструменту {api_type}:

ЗАДАЧА: {adapted_task}

Используйте модель: {model_name if model_name else 'выберите подходящую'}

После выполнения задачи, проанализируйте результат и предоставьте краткий отчет.
Учтите, что результат будет использоваться формой разума типа: {intelligence_type}
"""
        
        # Отправляем инструкцию ассистенту с учетом типа разума
        result = self.send_instruction(delegation_instruction, INTELLIGENCE_TYPE_AI)
        
        # Если ассистент успешно принял задачу, теперь нам нужно её выполнить
        if result.get("success", False):
            try:
                log_action(f"Выполнение делегированной задачи через {api_type} для {intelligence_type}")
                
                # Используем model_selector для выбора оптимальной модели и API
                if not model_name:
                    _, model_name, api_url = model_selector.select_optimal_api_and_model(
                        text=task,
                        preferred_api=api_type
                    )
                
                # Здесь должна быть логика выполнения задачи через выбранный API
                # Для демонстрации возвращаем заглушку
                task_result = {
                    "success": True,
                    "api_type": api_type,
                    "model": model_name,
                    "task": task,
                    "adapted_task": adapted_task,
                    "intelligence_type": intelligence_type,
                    "result": "Задача выполнена (демо-режим)",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Адаптируем результат для указанного типа разума
                if intelligence_type != INTELLIGENCE_TYPE_HUMAN:
                    task_result["adapted_result"] = self.intelligence_adapter.adapt_message(
                        task_result["result"], intelligence_type
                    )
                
                log_result(f"Задача делегирована и выполнена через {api_type} для {intelligence_type}")
                return task_result
                
            except Exception as e:
                log_error(f"Ошибка при выполнении делегированной задачи через {api_type}", e)
                return {"error": str(e), "success": False}
        else:
            return result
    
    def update_instructions(self) -> bool:
        """
        Обновляет инструкции для ассистента из файла TODO.md.
        
        Returns:
            bool: True, если инструкции успешно обновлены
        """
        log_action("Обновление инструкций для ассистента")
        
        try:
            new_instructions = self._load_instructions()
            
            if new_instructions != self.instructions:
                self.instructions = new_instructions
                
                # Обновляем системное сообщение в истории
                if self.message_history:
                    system_prompt = f"""Вы ассистент главного координатора проекта MUFU.
                    
{self.instructions}

Текущая дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
Вы должны помогать выполнять инструкции главного координатора и управлять другими AI-инструментами.
Отвечайте точно и по делу, предлагайте конкретные решения."""
                    
                    self.message_history[0] = {
                        "role": "system",
                        "content": system_prompt
                    }
                    
                log_result("Инструкции для ассистента обновлены")
                return True
            else:
                log_result("Инструкции для ассистента не изменились")
                return True
                
        except Exception as e:
            log_error("Ошибка при обновлении инструкций", e)
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получает текущий статус ассистента.
        
        Returns:
            Dict[str, Any]: Информация о статусе ассистента
        """
        return {
            "name": self.assistant_name,
            "role": self.assistant_role,
            "available": self.is_available,
            "model": self.model,
            "instructions_length": len(self.instructions),
            "message_history_length": len(self.message_history),
            "created_at": self.assistant_created_at.isoformat()
        }

    def save_conversation(self, file_path: Optional[str] = None) -> str:
        """
        Сохраняет историю обмена сообщениями с ассистентом в файл.
        
        Args:
            file_path: Путь для сохранения файла (опционально)
            
        Returns:
            str: Путь к сохраненному файлу
        """
        log_action("Сохранение истории обмена сообщениями с ассистентом")
        
        try:
            if not file_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = f"e:/mufu/logs/assistant_conversation_{timestamp}.json"
            
            conversation_data = {
                "assistant": {
                    "name": self.assistant_name,
                    "role": self.assistant_role,
                    "model": self.model,
                    "created_at": self.assistant_created_at.isoformat()
                },
                "messages": self.message_history,
                "exported_at": datetime.now().isoformat()
            }
            
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            
            log_result(f"История обмена сообщениями сохранена в: {file_path}")
            return file_path
            
        except Exception as e:
            log_error("Ошибка при сохранении истории обмена сообщениями", e)
            return ""
    
    def reasoning_completion(self, task: str, intelligence_type: Optional[str] = None,
                           step_by_step: bool = True) -> Dict[str, Any]:
        """
        Запрашивает структурированное рассуждение у модели для решения задачи.
        Оптимизировано для reasoning моделей, таких как Reka-Flash-3-21B-Reasoning.
        
        Args:
            task: Задача или вопрос для рассуждения
            intelligence_type: Тип формы разума (по умолчанию - текущий тип)
            step_by_step: Требовать ли пошаговое рассуждение
            
        Returns:
            Dict[str, Any]: Результат рассуждения или информация об ошибке
        """
        if not intelligence_type:
            intelligence_type = self.current_intelligence_type
            
        log_action(f"Запрос структурированного рассуждения от модели для {intelligence_type}")
        
        # Формируем специальный запрос для модели reasoning
        reasoning_prompt = task
        if step_by_step:
            reasoning_prompt = f"""Решите следующую задачу, используя пошаговое рассуждение:

{task}

Пожалуйста, выполните следующие шаги:
1. Определите, какую информацию нужно найти или какую проблему решить.
2. Составьте план решения.
3. Выполните необходимые рассуждения или вычисления шаг за шагом.
4. Сформулируйте окончательный ответ.
"""
        
        try:
            # Проверяем доступность API
            if not self.is_available:
                self._check_availability()
                if not self.is_available:
                    return {"error": "API недоступен", "success": False}
            
            # Подготавливаем сообщения для llama.cpp в формате chatML
            messages = [
                {
                    "role": "system",
                    "content": "Вы логический ассистент, который помогает решать задачи через структурированные рассуждения. Используйте последовательные логические шаги для достижения надежного решения."
                },
                {
                    "role": "user",
                    "content": reasoning_prompt
                }
            ]
            
            # Параметры для reasoning модели
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key and self.api_key != "NA":
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            # Специальные параметры для reasoning моделей
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": REASONING_TEMPERATURE,  # Низкая температура для логических рассуждений
                "top_p": REASONING_TOP_P,
                "max_tokens": REASONING_MAX_TOKENS,
                "stream": False
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    reasoning = result["choices"][0]["message"].get("content", "")
                    
                    # Адаптируем ответ для указанного типа разума
                    if intelligence_type != INTELLIGENCE_TYPE_AI:
                        reasoning = self.intelligence_adapter.adapt_message(reasoning, intelligence_type)
                    
                    log_result(f"Получено структурированное рассуждение (адаптировано для {intelligence_type})")
                    
                    return {
                        "success": True,
                        "reasoning": reasoning,
                        "intelligence_type": intelligence_type,
                        "usage": result.get("usage", {})
                    }
                else:
                    error_msg = "Некорректный формат ответа от API"
                    log_error(error_msg, Exception("Отсутствует поле choices в ответе"))
                    return {"error": error_msg, "success": False}
            else:
                error_msg = f"Ошибка при отправке запроса к API: {response.status_code}"
                log_error(error_msg, Exception(response.text))
                return {"error": error_msg, "success": False}
                
        except requests.exceptions.Timeout:
            error_msg = "Таймаут при запросе структурированного рассуждения"
            log_error(error_msg, Exception("Таймаут превышен"))
            return {"error": error_msg, "success": False}
        except Exception as e:
            log_error("Ошибка при запросе структурированного рассуждения", e)
            return {"error": str(e), "success": False}
    
    def function_calling(self, task: str, functions: List[Dict[str, Any]],
                        intelligence_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Выполняет запрос к модели с поддержкой функциональных вызовов (function calling).
        Позволяет модели самостоятельно выбрать нужную функцию и заполнить ее аргументы.
        
        Args:
            task: Задача для выполнения
            functions: Список доступных функций в формате OpenAI
            intelligence_type: Тип формы разума (по умолчанию - текущий тип)
            
        Returns:
            Dict[str, Any]: Результат выполнения функции или информация об ошибке
        """
        if not intelligence_type:
            intelligence_type = self.current_intelligence_type
            
        log_action(f"Запрос функционального вызова от модели для {intelligence_type}")
        
        try:
            # Проверяем доступность API
            if not self.is_available:
                self._check_availability()
                if not self.is_available:
                    return {"error": "API недоступен", "success": False}
            
            # Подготавливаем сообщения для llama.cpp в формате chatML
            messages = [
                {
                    "role": "system",
                    "content": "Вы ассистент с доступом к функциям. Используйте доступные функции для выполнения задач пользователя."
                },
                {
                    "role": "user",
                    "content": task
                }
            ]
            
            # Параметры для function calling
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key and self.api_key != "NA":
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            # Специальные параметры для function calling
            payload = {
                "model": self.model,
                "messages": messages,
                "functions": functions,
                "temperature": FUNCTION_CALLING_TEMPERATURE,
                "response_format": FUNCTION_JSON_SCHEMA,
                "stream": False
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    function_response = result["choices"][0]["message"]
                    
                    # Извлекаем результат функционального вызова
                    function_name = None
                    function_args = {}
                    
                    if "function_call" in function_response:
                        function_call = function_response["function_call"]
                        function_name = function_call.get("name", "")
                        
                        try:
                            function_args = json.loads(function_call.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            function_args = {"error": "Невозможно разобрать аргументы как JSON"}
                    
                    log_result(f"Получен функциональный вызов: {function_name}")
                    
                    # Адаптируем только описательную часть ответа для указанного типа разума
                    content = function_response.get("content", "")
                    if intelligence_type != INTELLIGENCE_TYPE_AI and content:
                        content = self.intelligence_adapter.adapt_message(content, intelligence_type)
                    
                    return {
                        "success": True,
                        "function_name": function_name,
                        "function_args": function_args,
                        "content": content,
                        "intelligence_type": intelligence_type,
                        "usage": result.get("usage", {})
                    }
                else:
                    error_msg = "Некорректный формат ответа от API"
                    log_error(error_msg, Exception("Отсутствует поле choices в ответе"))
                    return {"error": error_msg, "success": False}
            else:
                error_msg = f"Ошибка при отправке запроса к API: {response.status_code}"
                log_error(error_msg, Exception(response.text))
                return {"error": error_msg, "success": False}
                
        except requests.exceptions.Timeout:
            error_msg = "Таймаут при запросе функционального вызова"
            log_error(error_msg, Exception("Таймаут превышен"))
            return {"error": error_msg, "success": False}
        except Exception as e:
            log_error("Ошибка при запросе функционального вызова", e)
            return {"error": str(e), "success": False}
            
    def stream_reasoning(self, task: str, intelligence_type: Optional[str] = None) -> Generator[str, None, None]:
        """
        Потоковый запрос рассуждения к модели с возвращением результатов по мере их генерации.
        Особенно полезно для больших reasoning моделей с длительным временем генерации.
        
        Args:
            task: Задача для рассуждения
            intelligence_type: Тип формы разума (по умолчанию - текущий тип)
            
        Yields:
            str: Части генерируемого рассуждения по мере их поступления
        """
        if not intelligence_type:
            intelligence_type = self.current_intelligence_type
            
        log_action(f"Запрос потокового рассуждения от модели для {intelligence_type}")
        
        try:
            # Проверяем доступность API
            if not self.is_available:
                self._check_availability()
                if not self.is_available:
                    yield "Ошибка: API недоступен"
                    return
            
            # Подготавливаем сообщения для llama.cpp в формате chatML
            messages = [
                {
                    "role": "system",
                    "content": "Вы логический ассистент, который помогает решать задачи через структурированные рассуждения. Рассуждайте пошагово."
                },
                {
                    "role": "user",
                    "content": task
                }
            ]
            
            # Параметры для потоковой обработки
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key and self.api_key != "NA":
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            # Специальные параметры для потоковой обработки
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": REASONING_TEMPERATURE,
                "stream": True,  # Потоковая обработка
                "top_p": REASONING_TOP_P,
            }
            
            # Отправляем запрос с потоковой обработкой
            response = requests.post(url, headers=headers, json=payload, stream=True, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code == 200:
                # Буфер для накопления частичных токенов
                buffer = ""
                # Для адаптации потоковых данных под тип разума используем подход с буферизацией
                # Каждые N токенов отправляем на адаптацию
                adaptation_buffer_size = 20
                
                # Обрабатываем потоковый ответ
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: ') and line_text != 'data: [DONE]':
                            data = json.loads(line_text[6:])
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    buffer += content
                                    
                                    # Если накоплен достаточный буфер или получили знак завершения предложения
                                    if len(buffer) >= adaptation_buffer_size or any(x in buffer for x in ['.', '!', '?', '\n']):
                                        # Для не-AI форм разума выполняем адаптацию
                                        if intelligence_type != INTELLIGENCE_TYPE_AI:
                                            # Упрощенная адаптация для потоковых данных
                                            adapted_content = self.intelligence_adapter.adapt_message(buffer, intelligence_type)
                                            yield adapted_content
                                        else:
                                            yield buffer
                                        
                                        buffer = ""  # Очищаем буфер
                
                # Отправляем оставшуюся часть буфера, если она есть
                if buffer:
                    if intelligence_type != INTELLIGENCE_TYPE_AI:
                        adapted_content = self.intelligence_adapter.adapt_message(buffer, intelligence_type)
                        yield adapted_content
                    else:
                        yield buffer
                
                log_result("Завершена генерация потокового рассуждения")
            else:
                error_msg = f"Ошибка при отправке запроса к API: {response.status_code}"
                log_error(error_msg, Exception(response.text))
                yield f"Ошибка: {error_msg}"
                
        except requests.exceptions.Timeout:
            error_msg = "Таймаут при запросе потокового рассуждения"
            log_error(error_msg, Exception("Таймаут превышен"))
            yield f"Ошибка: {error_msg}"
        except Exception as e:
            log_error("Ошибка при запросе потокового рассуждения", e)
            yield f"Ошибка: {str(e)}"

# Создаем экземпляр менеджера ассистента для использования в других модулях
assistant = AssistantManager()

if __name__ == "__main__":
    # Пример использования
    from app.logger import setup_logging
    
    setup_logging()
    
    # Создаем менеджера ассистента
    manager = AssistantManager()
    
    # Проверяем статус
    print("Статус ассистента:", manager.get_status())
    
    # Устанавливаем тип разума
    manager.set_intelligence_type(INTELLIGENCE_TYPE_AI)
    
    # Отправляем простую инструкцию
    if manager.is_available:
        result = manager.send_instruction(
            "Опишите свои возможности как ассистента главного координатора проекта MUFU."
        )
        
        if result.get("success", False):
            print("\nОтвет ассистента:")
            print(result["response"])
        else:
            print("\nОшибка при взаимодействии с ассистентом:", result.get("error"))
            
        # Делегируем тестовую задачу
        task_result = manager.delegate_task(
            "Сгенерируйте краткое описание проекта на основе инструкций.",
            "ollama",
            "llama3"
        )
        
        print("\nРезультат делегирования задачи:")
        print(json.dumps(task_result, indent=2, ensure_ascii=False))
        
        # Сохраняем историю обмена сообщениями
        saved_path = manager.save_conversation()
        print(f"\nИстория обмена сообщениями сохранена в: {saved_path}")
    else:
        print("Ассистент недоступен. Пожалуйста, проверьте настройки API.")