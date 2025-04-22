"""
Тестирование системы логирования.
Этот скрипт демонстрирует возможности системы логирования проекта MUFU.
"""
import os
import sys

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
from app.logger import (
    setup_logging, log_goal, log_action, log_decision, log_result, 
    log_error, log_info, export_session_log, get_session_summary
)

def simulate_video_creation_workflow():
    """
    Симулирует рабочий процесс создания видео для демонстрации логирования.
    Записывает различные типы событий с контекстом.
    """
    # Записываем цель
    log_goal("Тестирование системы логирования", {
        "purpose": "Демонстрация возможностей логирования для проекта MUFU",
        "target_audience": "Разработчики и ИИ-ассистенты"
    })
    
    # Демонстрация логирования действий
    log_action("Загрузка тестовых данных", {
        "data_type": "sample_document.pdf",
        "size": "1.2 MB"
    })
    time.sleep(0.5)  # Имитация задержки
    
    # Демонстрация логирования решений
    log_decision("Выбор движка AI для обработки текста: Ollama", 
                alternatives=["Ollama", "LlamaCPP", "YandexGPT"],
                reasoning="Ollama обеспечивает лучший баланс между скоростью и качеством для текущей задачи")
    
    # Демонстрация логирования результатов
    log_result("Текст успешно загружен и предварительно обработан", {
        "tokens": 1250,
        "paragraphs": 12,
        "processing_time": "0.83 сек"
    })
    
    # Симулируем обработку нескольких сцен
    for scene_index in range(3):
        log_goal(f"Обработка тестовой сцены {scene_index+1}")
        
        # Различные этапы обработки
        log_action(f"Упрощение текста для сцены {scene_index+1}")
        time.sleep(0.3)  # Имитация работы
        
        # Иногда симулируем ошибки
        if scene_index == 1:
            try:
                # Симулируем ошибку
                raise ValueError("Тестовая ошибка при обработке текста")
            except Exception as e:
                log_error(f"Ошибка при обработке сцены {scene_index+1}", e)
                log_decision("Использование исходного текста вместо упрощенного", 
                           reasoning="Возникла ошибка при попытке упростить текст")
        else:
            log_result(f"Текст для сцены {scene_index+1} успешно упрощен", {
                "original_length": 500,
                "simplified_length": 300,
                "time_taken": "0.5 сек"
            })
        
        # Генерация изображения
        log_action(f"Генерация изображения для сцены {scene_index+1}")
        time.sleep(0.4)
        log_result(f"Изображение для сцены {scene_index+1} успешно создано", {
            "path": f"outputs/images/scene_{scene_index+1:03d}.png",
            "dimensions": "1024x768",
            "time_taken": "1.2 сек"
        })
        
        # Генерация озвучки
        log_action(f"Генерация аудио для сцены {scene_index+1}")
        time.sleep(0.3)
        log_result(f"Аудио для сцены {scene_index+1} успешно создано", {
            "path": f"outputs/audio/scene_{scene_index+1:03d}.mp3",
            "duration": f"{scene_index+1 * 10} сек",
            "time_taken": "0.8 сек"
        })
        
        # Сборка слайда
        log_action(f"Сборка слайда для сцены {scene_index+1}")
        time.sleep(0.2)
        log_result(f"Слайд {scene_index+1} успешно собран", {
            "duration": f"{scene_index+1 * 12} сек"
        })
    
    # Финальная сборка
    log_action("Компоновка финального видео")
    time.sleep(0.8)
    log_result("Видео успешно скомпоновано", {
        "duration": "45 сек",
        "file_size": "12.5 MB",
        "output_path": "outputs/final_video.mp4"
    })
    
    # Записываем информационное сообщение
    log_info("Тестирование системы логирования завершено", {
        "total_scenes": 3,
        "total_duration": "45 сек"
    })

def main():
    print("Тестирование системы логирования")
    print("=" * 80)
    
    # Настраиваем систему логирования
    setup_logging(log_to_console=True)
    
    # Симулируем рабочий процесс
    try:
        simulate_video_creation_workflow()
        
        # Выводим сводку сессии
        summary = get_session_summary()
        print("\n" + "=" * 80)
        print("СВОДКА СЕССИИ ЛОГИРОВАНИЯ:")
        print(f"- Дата: {summary['date']}")
        print(f"- Всего событий: {summary['total_events']}")
        print(f"- Цели: {summary['counts']['GOAL']}")
        print(f"- Действия: {summary['counts']['ACTION']}")
        print(f"- Результаты: {summary['counts']['RESULT']}")
        print(f"- Ошибки: {summary['counts']['ERROR']}")
        print("=" * 80)
        
        # Экспортируем логи в оба формата для демонстрации
        yaml_path = export_session_log("yaml")
        json_path = export_session_log("json")
        
        print(f"\nЛоги экспортированы в YAML: {yaml_path}")
        print(f"Логи экспортированы в JSON: {json_path}")
        
        return True
    except Exception as e:
        print(f"Ошибка при выполнении теста: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)