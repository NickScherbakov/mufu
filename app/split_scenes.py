import re

def split_scenes(text):
    """Разделяет текст на смысловые блоки (сцены) по абзацам."""
    # Разделяем по двойным (или более) переносам строки
    # Также убираем лишние пробелы/переносы в начале/конце каждого блока
    scenes = [scene.strip() for scene in re.split(r'\n\s*\n', text) if scene.strip()]
    return scenes
