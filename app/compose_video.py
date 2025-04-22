from moviepy.editor import *
import os

def assemble_slide(image_path, audio_path, subtitle_text, duration=None):
    """
    Создает один видеослайд с изображением, аудио и субтитрами.
    
    Args:
        image_path: Путь к файлу изображения
        audio_path: Путь к аудиофайлу
        subtitle_text: Текст субтитров
        duration: Продолжительность слайда в секундах (если None, берется из аудио)
        
    Returns:
        VideoClip: объект видеоклипа moviepy
    """
    try:
        # Загружаем аудио для определения длительности
        audio = AudioFileClip(audio_path)
        
        # Если длительность не указана, берем из аудио + небольшой запас
        if duration is None:
            duration = audio.duration + 1.0  # +1 секунда для комфортного просмотра
        
        # Загружаем изображение и устанавливаем длительность
        image = ImageClip(image_path).set_duration(duration)
        
        # Определяем размеры видео и масштабируем изображение
        target_width, target_height = 1920, 1080  # Full HD
        image = image.resize(height=target_height)
        
        # Центрируем изображение, если оно не соответствует соотношению сторон
        if image.w < target_width:
            # Создаем черный фон
            bg = ColorClip((target_width, target_height), color=(0, 0, 0))
            bg = bg.set_duration(duration)
            
            # Размещаем изображение по центру
            image = image.set_position('center')
            image = CompositeVideoClip([bg, image])
        
        # Создаем субтитры
        # Разбиваем длинный текст на строки для лучшей читаемости
        subtitle_lines = []
        words = subtitle_text.split()
        current_line = ""
        
        # Примерно 7-8 слов в строке
        for word in words:
            if len(current_line.split()) < 7:
                current_line += " " + word if current_line else word
            else:
                subtitle_lines.append(current_line)
                current_line = word
        
        if current_line:
            subtitle_lines.append(current_line)
        
        # Объединяем строки с переносами
        formatted_subtitles = "\n".join(subtitle_lines)
        
        # Создаем клип с субтитрами
        text_clip = TextClip(
            formatted_subtitles, 
            fontsize=32, 
            color='white',
            bg_color='rgba(0,0,0,0.5)',  # Полупрозрачный черный фон
            font='Arial',
            method='caption',  # Используем caption для поддержки многострочного текста
            align='center',
            size=(target_width, None)  # Фиксированная ширина, высота автоматическая
        ).set_position(('center', 'bottom')).set_duration(duration)
        
        # Объединяем изображение с субтитрами
        video = CompositeVideoClip([image, text_clip])
        
        # Добавляем аудио
        video = video.set_audio(audio)
        
        return video
        
    except Exception as e:
        print(f"Ошибка при сборке слайда: {e}")
        return None

def compose_video(slides, output_path, fps=24):
    """
    Собирает несколько слайдов в одно видео.
    
    Args:
        slides: Список объектов VideoClip
        output_path: Путь для сохранения итогового видео
        fps: Кадров в секунду для итогового видео
        
    Returns:
        bool: True при успешном создании, иначе False
    """
    try:
        if not slides:
            print("Нет слайдов для сборки видео")
            return False
        
        # Объединяем все слайды в один клип
        final_clip = concatenate_videoclips(slides)
        
        # Добавляем плавные переходы между слайдами
        # (Примечание: в текущей версии не реализовано, 
        # может быть добавлено позже через cross_fadein)
        
        # Сохраняем видео
        final_clip.write_videofile(
            output_path, 
            fps=fps, 
            codec='libx264', 
            audio_codec='aac',
            threads=4,
            preset='medium'  # Компромисс между качеством и скоростью
        )
        
        print(f"Видео успешно сохранено: {output_path}")
        return True
        
    except Exception as e:
        print(f"Ошибка при сборке видео: {e}")
        return False
