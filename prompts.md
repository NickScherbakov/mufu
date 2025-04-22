# prompts.md

## 🎯 Цель проекта
Создать инструмент, который преобразует текстовые документы (например, методики решения задач) в видеопрезентации, объясняющие сложные концепции с помощью картинок, анимации и синтезированного голоса.

## 🧱 Компоненты и архитектура

**Основные этапы:**
1. Извлечение текста из документа (PDF, DOCX, TXT)
2. Разделение текста на смысловые блоки ("слайды")
3. Переформулирование каждого блока в упрощённой, понятной форме
4. Генерация иллюстраций к каждому блоку
5. Озвучка каждого блока
6. Сборка видео слайд за слайдом

**Мини-архитектура (инструменты локально):**
- **LLM**: `llama.cpp` или `Ollama` (например, `mistral`, `llama3`, `phi`)
- **TTS**: `coqui.ai TTS`, `Bark`, `Tortoise TTS` (любая свободная модель)
- **Изображения**: `Stable Diffusion` (через diffusers или Web UI)
- **Видео**: `moviepy`, `manim`, `ffmpeg`

---

## ⚙️ Структура проекта

```
project_root/
│
├── app/
│   ├── extract_text.py         # Извлечение текста
│   ├── split_scenes.py         # Деление на смысловые блоки
│   ├── simplify_text.py        # Обработка текста через LLM
│   ├── generate_image.py       # Генерация изображений
│   ├── generate_voice.py       # Озвучка текста
│   ├── compose_video.py        # Сборка слайдов в видео
│   └── utils.py                # Общие утилиты
│
├── inputs/
│   └── document.pdf            # Пример входного документа
│
├── outputs/
│   └── final_video.mp4         # Результат
│
├── prompts.md                 # Документация (этот файл)
└── requirements.txt
```

---

## 📌 Промпты и подсказки

### 1. Упрощение текста (LLM)
```text
Выступай как учитель, который объясняет сложную идею простым языком. Вот блок текста из методики:

"{{исходный_абзац}}"

Преобразуй его в понятное объяснение для школьника.
```

### 2. Генерация изображения
```text
Создай иллюстрацию, которая поможет объяснить следующую идею:

"{{упрощённый_абзац}}"

Изображение должно быть простым, без текста, с фокусом на ключевой концепции.
```

### 3. Озвучка
```text
Используй TTS модель, чтобы озвучить упрощённый текст:
"{{упрощённый_абзац}}"
```

### 4. Сборка видео (moviepy)
```python
from moviepy.editor import *

def assemble_slide(image_path, audio_path, subtitle_text, duration=10):
    image = ImageClip(image_path).set_duration(duration).resize(height=720)
    audio = AudioFileClip(audio_path)
    text = TextClip(subtitle_text, fontsize=32, color='white', bg_color='black') \
           .set_position(('center', 'bottom')).set_duration(duration)
    return CompositeVideoClip([image, text]).set_audio(audio)
```

---

## ✅ Пример пайплайна (main.py)
```python
text = extract_text("inputs/document.pdf")
scenes = split_scenes(text)
slides = []

for i, scene in enumerate(scenes):
    simplified = simplify(scene)
    image_path = generate_image(simplified, i)
    audio_path = generate_voice(simplified, i)
    slide = assemble_slide(image_path, audio_path, simplified)
    slides.append(slide)

final = concatenate_videoclips(slides)
final.write_videofile("outputs/final_video.mp4")
```

---

## 💻 Настройки для локального запуска
- `Ollama` должен быть запущен на `localhost:11434`
- Используемая модель (`llama3`, `mistral`, и т.д.) — должна быть загружена
- Все генерации выполняются офлайн
- Минимум 16ГБ ОЗУ, желательно наличие GPU (но можно и на CPU)

---

## 📌 Дополнительно
- Возможна интеграция анимации (`manim`, `AnimateDiff`) на следующих этапах
- Можно добавить UI на `Gradio` или `Streamlit` позже

---

Готово для реализации с GitHub Copilot. Начинай с создания `main.py`, реализуя модули поэтапно.

https://chatgpt.com/share/68054790-f068-800e-8fac-b950faf99e35