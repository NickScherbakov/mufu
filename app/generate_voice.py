import os
import requests
import subprocess
import sys
import tempfile
from pathlib import Path

def generate_voice(text, scene_index, output_dir="outputs"):
    """Генерирует аудиофайл с озвучкой текста."""
    # Создаем директорию для аудио, если не существует
    audio_dir = os.path.join(output_dir, "audio")
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
    
    # Формируем имя файла по индексу сцены
    output_filename = f"scene_{scene_index:03d}.mp3"
    output_path = os.path.join(audio_dir, output_filename)
    
    # Если файл уже существует, возвращаем путь к нему (кеширование)
    if os.path.exists(output_path):
        print(f"Аудио для сцены {scene_index} уже существует, использую его.")
        return output_path
    
    # Пытаемся использовать разные методы TTS в порядке приоритета
    if try_edge_tts(text, output_path):
        return output_path
    
    print("Все методы генерации аудио не удались. Возвращаю путь к файлу, который должен был быть создан.")
    return None

def try_edge_tts(text, output_path):
    """Пытается использовать edge-tts (Microsoft Edge TTS)."""
    try:
        # Проверяем, установлен ли edge-tts
        try:
            import edge_tts
            has_edge_tts = True
        except ImportError:
            has_edge_tts = False
        
        if has_edge_tts:
            # Используем async функционал edge-tts через sync обертку
            import asyncio
            from edge_tts import Communicate
            
            async def _synthesize_speech():
                communicate = Communicate(text, "ru-RU-DmitryNeural")
                await communicate.save(output_path)
            
            # Запускаем асинхронную функцию синхронно
            asyncio.run(_synthesize_speech())
            print(f"Аудио успешно сгенерировано через edge-tts: {output_path}")
            return True
        else:
            # Пытаемся использовать edge-tts через subprocess (если он установлен в системе)
            try:
                subprocess.run(
                    [
                        "edge-tts",
                        "--voice", "ru-RU-DmitryNeural",
                        "--text", text,
                        "--write-media", output_path
                    ],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"Аудио успешно сгенерировано через edge-tts CLI: {output_path}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Ошибка при использовании edge-tts CLI: {e}")
                return False
            except FileNotFoundError:
                print("edge-tts не найден в системе.")
                return False
    except Exception as e:
        print(f"Ошибка при генерации аудио с edge-tts: {e}")
        return False
