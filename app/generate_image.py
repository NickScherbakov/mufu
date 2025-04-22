import os
import requests
import json
from PIL import Image
import io
import base64
import time
from app.utils import get_env

# Используем Stable Diffusion через API
# Это предполагает, что у вас запущен SD Web UI с расширением API
# По умолчанию адрес: http://127.0.0.1:7860/sdapi/v1/txt2img
# но используем из .env если задано

def generate_image(text, scene_index, output_dir="outputs", api_url=None):
    """Генерирует изображение по тексту используя Stable Diffusion."""
    # Если API URL не указан, берем из переменных окружения или используем значение по умолчанию
    if api_url is None:
        api_url = get_env("sd_api_base", "http://127.0.0.1:7860/sdapi/v1/txt2img")
    
    # Создаем директорию для изображений, если не существует
    images_dir = os.path.join(output_dir, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    # Формируем имя файла по индексу сцены
    output_filename = f"scene_{scene_index:03d}.png"
    output_path = os.path.join(images_dir, output_filename)
    
    # Если файл уже существует, возвращаем путь к нему (кеширование)
    if os.path.exists(output_path):
        print(f"Изображение для сцены {scene_index} уже существует, использую его.")
        return output_path
    
    # Создаем промпт для Stable Diffusion
    prompt = f"""Create a simple, clear educational illustration that explains the following concept:
    {text}
    Style: Simple, educational, clean background, suitable for teaching"""
    
    payload = {
        "prompt": prompt,
        "negative_prompt": "text, watermark, low quality, blurry",
        "width": 1024,
        "height": 768,
        "steps": 30,
        "cfg_scale": 7.5
    }
    
    try:
        # Проверка наличия API
        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            # Если локальный SD недоступен, генерируем заглушку
            print(f"Предупреждение: Не удалось подключиться к Stable Diffusion API по адресу {api_url}.")
            print("Генерирую заглушку вместо изображения...")
            generate_placeholder_image(output_path, text)
            return output_path
        
        # Обработка ответа API
        result = response.json()
        
        if 'images' in result and len(result['images']) > 0:
            # Декодируем base64 изображение
            image_data = base64.b64decode(result['images'][0])
            image = Image.open(io.BytesIO(image_data))
            
            # Сохраняем изображение
            image.save(output_path)
            print(f"Изображение успешно сгенерировано и сохранено: {output_path}")
            return output_path
        else:
            print("Ошибка: Не удалось получить изображение от API")
            generate_placeholder_image(output_path, text)
            return output_path
            
    except Exception as e:
        print(f"Ошибка при генерации изображения: {e}")
        generate_placeholder_image(output_path, text)
        return output_path

def generate_placeholder_image(output_path, text):
    """Создает простое изображение-заглушку с текстом."""
    try:
        # Создаем пустое изображение
        width, height = 1024, 768
        image = Image.new('RGB', (width, height), color=(240, 240, 240))
        
        # Сохраняем изображение
        image.save(output_path)
        print(f"Создано изображение-заглушка: {output_path}")
        return True
    except Exception as e:
        print(f"Ошибка при создании изображения-заглушки: {e}")
        return False
