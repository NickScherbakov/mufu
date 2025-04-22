from app.extract_text import extract_text
from app.split_scenes import split_scenes
from app.simplify_text import simplify
from app.generate_image import generate_image
from app.generate_voice import generate_voice
from app.compose_video import assemble_slide, compose_video
from moviepy.editor import concatenate_videoclips
import os
import argparse
import concurrent.futures
import time
import datetime
from app.utils import get_env
from app.logger import (
    setup_logging, log_goal, log_action, log_decision, log_result, log_error, log_info,
    export_session_log, get_session_summary
)

# Настройки по умолчанию
INPUT_FILE_PATH = "inputs/document.pdf"  # Замените на реальный путь к вашему файлу
OUTPUT_DIR = "outputs"
OUTPUT_VIDEO_PATH = os.path.join(OUTPUT_DIR, "final_video.mp4")

# Настройки AI движков
AVAILABLE_ENGINES = ["ollama", "llamacpp", "yandexgpt"]
DEFAULT_ENGINE = "ollama"

def parse_arguments():
    """Обработка аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Создание обучающих видео на основе текста с помощью AI.")
    parser.add_argument("-i", "--input", help="Путь к входному файлу (PDF, DOCX, TXT)", default=INPUT_FILE_PATH)
    parser.add_argument("-o", "--output", help="Путь для сохранения выходного видео", default=OUTPUT_VIDEO_PATH)
    parser.add_argument("-d", "--output-dir", help="Директория для промежуточных файлов", default=OUTPUT_DIR)
    parser.add_argument("-e", "--engine", help=f"AI движок для упрощения текста ({', '.join(AVAILABLE_ENGINES)})", 
                       choices=AVAILABLE_ENGINES, default=DEFAULT_ENGINE)
    parser.add_argument("-m", "--model", help="Название модели для выбранного движка (опционально)")
    parser.add_argument("-p", "--parallel", help="Обрабатывать сцены параллельно", action="store_true")
    parser.add_argument("--max-workers", help="Максимальное количество параллельных процессов", type=int, default=3)
    parser.add_argument("--log-level", help="Уровень детализации логов (INFO, DEBUG, WARNING, ERROR)", default="INFO")
    parser.add_argument("--export-log", help="Экспортировать логи в указанный формат после завершения (json, yaml)", 
                        choices=["json", "yaml"], default=None)
    return parser.parse_args()

def process_scene(scene, scene_index, args):
    """Обработка одной сцены с использованием выбранного движка AI."""
    scene_id = f"{scene_index+1}"
    log_goal(f"Обработка сцены {scene_id}", {
        "scene_index": scene_index,
        "scene_preview": scene[:100] + "..." if len(scene) > 100 else scene,
        "engine": args.engine,
        "model": args.model
    })
    
    # 1. Упрощение текста
    log_action(f"Упрощение текста для сцены {scene_id}", {
        "engine": args.engine,
        "model": args.model,
        "text_length": len(scene)
    })
    
    start_time = time.time()
    simplified = simplify(scene, engine=args.engine, model_name=args.model)
    elapsed = time.time() - start_time
    
    if not simplified:
        log_error(f"Не удалось упростить текст для сцены {scene_id}", Exception("Нулевой результат от API"))
        log_decision("Использование оригинального текста вместо упрощенного", 
                    reasoning="API вернуло пустой результат или произошла ошибка")
        simplified = scene
    else:
        log_result(f"Текст для сцены {scene_id} успешно упрощен", {
            "original_length": len(scene),
            "simplified_length": len(simplified),
            "time_taken": f"{elapsed:.2f} сек",
            "simplified_preview": simplified[:100] + "..." if len(simplified) > 100 else simplified
        })

    # 2. Генерация изображения
    log_action(f"Генерация изображения для сцены {scene_id}")
    start_time = time.time()
    image_path = generate_image(simplified, scene_index, args.output_dir)
    elapsed = time.time() - start_time
    
    if not image_path:
        log_error(f"Не удалось сгенерировать изображение для сцены {scene_id}")
        return None
    else:
        log_result(f"Изображение для сцены {scene_id} успешно сгенерировано", {
            "image_path": image_path,
            "time_taken": f"{elapsed:.2f} сек"
        })

    # 3. Генерация озвучки
    log_action(f"Генерация озвучки для сцены {scene_id}")
    start_time = time.time()
    audio_path = generate_voice(simplified, scene_index, args.output_dir)
    elapsed = time.time() - start_time
    
    if not audio_path:
        log_error(f"Не удалось сгенерировать озвучку для сцены {scene_id}")
        return None
    else:
        log_result(f"Озвучка для сцены {scene_id} успешно сгенерирована", {
            "audio_path": audio_path,
            "time_taken": f"{elapsed:.2f} сек"
        })

    # 4. Сборка слайда
    log_action(f"Сборка слайда для сцены {scene_id}")
    start_time = time.time()
    slide = assemble_slide(image_path, audio_path, simplified)
    elapsed = time.time() - start_time
    
    if not slide:
        log_error(f"Не удалось собрать слайд для сцены {scene_id}")
        return None
    else:
        log_result(f"Слайд для сцены {scene_id} успешно собран", {
            "time_taken": f"{elapsed:.2f} сек",
            "duration": f"{slide.duration:.2f} сек" if hasattr(slide, 'duration') else "Неизвестно"
        })
        
    return slide

def main():
    # Получаем аргументы командной строки
    args = parse_arguments()
    
    # Настраиваем логирование
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    setup_logging(log_to_console=True, log_level=log_level)
    
    # Записываем начальную информацию
    log_goal("Создание обучающего видео из текстового документа", {
        "input_file": args.input,
        "output_file": args.output,
        "engine": args.engine,
        "model": args.model,
        "parallel_processing": args.parallel,
        "max_workers": args.max_workers if args.parallel else 1
    })
    
    start_time_total = time.time()
    
    # Убедимся, что директория outputs существует
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        log_action(f"Создана директория для выходных файлов: {args.output_dir}")

    log_action(f"Извлечение текста из файла {args.input}")
    text_start_time = time.time()
    text = extract_text(args.input)
    text_time = time.time() - text_start_time

    if not text:
        log_error("Не удалось извлечь текст из документа", Exception("Пустой результат извлечения"))
        return

    log_result("Текст успешно извлечен из документа", {
        "chars": len(text),
        "time_taken": f"{text_time:.2f} сек"
    })
    
    log_action("Разделение текста на сцены")
    split_start_time = time.time()
    scenes = split_scenes(text)
    split_time = time.time() - split_start_time
    
    if not scenes:
        log_error("Не удалось разделить текст на сцены", Exception("Пустой результат разделения"))
        return
        
    log_result("Текст успешно разделен на сцены", {
        "scene_count": len(scenes),
        "avg_scene_length": sum(len(scene) for scene in scenes) / len(scenes),
        "time_taken": f"{split_time:.2f} сек"
    })

    # 3. Обработка сцен (последовательно или параллельно)
    slides = []
    
    parallel_decision = "параллельно" if args.parallel else "последовательно"
    log_decision(f"Обработка сцен {parallel_decision}", 
                reasoning="Выбрано пользователем через аргумент --parallel" if args.parallel 
                else "Последовательная обработка (по умолчанию)")
    
    if args.parallel:
        log_action(f"Запуск параллельной обработки сцен ({args.max_workers} потоков)")
        
        scene_results = []
        scene_start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            # Запускаем обработку всех сцен параллельно
            future_to_scene = {
                executor.submit(process_scene, scene, i, args): i 
                for i, scene in enumerate(scenes)
            }
            
            # Получаем результаты по мере их готовности
            for future in concurrent.futures.as_completed(future_to_scene):
                scene_index = future_to_scene[future]
                try:
                    slide = future.result()
                    if slide:
                        scene_results.append((scene_index, slide))
                        log_info(f"Сцена {scene_index+1} обработана успешно")
                    else:
                        log_error(f"Сцена {scene_index+1} не была обработана", 
                                 Exception("Возвращено значение None"))
                except Exception as e:
                    log_error(f"Ошибка при обработке сцены {scene_index+1}", e)
        
        # Сортируем результаты по индексу сцены и добавляем в список слайдов
        scene_results.sort(key=lambda x: x[0])
        slides = [result[1] for result in scene_results]
        
        scene_time = time.time() - scene_start_time
        log_result("Параллельная обработка сцен завершена", {
            "processed_scenes": len(slides),
            "failed_scenes": len(scenes) - len(slides),
            "time_taken": f"{scene_time:.2f} сек"
        })
    else:
        # Последовательная обработка сцен
        log_action("Запуск последовательной обработки сцен")
        scene_start_time = time.time()
        
        for i, scene in enumerate(scenes):
            slide = process_scene(scene, i, args)
            if slide:
                slides.append(slide)
        
        scene_time = time.time() - scene_start_time
        log_result("Последовательная обработка сцен завершена", {
            "processed_scenes": len(slides),
            "failed_scenes": len(scenes) - len(slides),
            "time_taken": f"{scene_time:.2f} сек"
        })

    # 4. Сборка финального видео
    if slides:
        log_action("Сборка финального видео")
        video_start_time = time.time()
        
        success = compose_video(slides, args.output, fps=24)
        video_time = time.time() - video_start_time
        
        if success:
            total_time = time.time() - start_time_total
            log_result("Финальное видео успешно собрано", {
                "output_path": args.output,
                "slide_count": len(slides),
                "video_assembly_time": f"{video_time:.2f} сек",
                "total_processing_time": f"{total_time:.2f} сек"
            })
        else:
            log_error("Ошибка при сборке финального видео")
    else:
        log_error("Не было создано ни одного слайда. Видео не собрано")
    
    # Экспортируем логи, если нужно
    if args.export_log:
        log_action(f"Экспорт логов в формате {args.export_log}")
        export_path = export_session_log(args.export_log)
        if export_path:
            log_result("Логи успешно экспортированы", {"export_path": export_path})
        else:
            log_error("Не удалось экспортировать логи")
    
    # Выводим сводку сессии
    summary = get_session_summary()
    print("\n" + "=" * 80)
    print("СВОДКА СЕССИИ:")
    print(f"- Дата: {summary['date']}")
    print(f"- Всего событий: {summary['total_events']}")
    print(f"- Цели: {summary['counts']['GOAL']}")
    print(f"- Действия: {summary['counts']['ACTION']}")
    print(f"- Результаты: {summary['counts']['RESULT']}")
    print(f"- Ошибки: {summary['counts']['ERROR']}")
    print("=" * 80)
    
    if args.export_log:
        print(f"Подробные логи экспортированы в: {export_path}")
    else:
        print("Для экспорта логов используйте параметр --export-log=yaml или --export-log=json")

if __name__ == "__main__":
    import logging
    main()
