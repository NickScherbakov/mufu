"""
Тестирование извлечения текста из PDF файла.
Этот скрипт проверяет, что приложение может корректно открыть 
и извлечь текст из файла inputs\short-ege1.pdf
"""
import os
import sys

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.extract_text import extract_text

def test_pdf_extraction():
    """Проверяет извлечение текста из PDF файла."""
    # Путь к тестовому PDF файлу
    pdf_path = os.path.join("inputs", "short-ege1.pdf")
    
    # Проверяем существование файла
    if not os.path.exists(pdf_path):
        print(f"ОШИБКА: Файл {pdf_path} не найден!")
        return False
    
    print(f"Файл {pdf_path} найден, пробуем извлечь текст...")
    
    # Извлекаем текст
    text = extract_text(pdf_path)
    
    # Проверяем, был ли извлечен текст
    if not text:
        print("ОШИБКА: Не удалось извлечь текст из PDF файла!")
        return False
      # Выводим статистику
    words = len(text.split())
    chars = len(text)
    print(f"\nСтатистика извлеченного текста:")
    print(f"- Символов: {chars}")
    print(f"- Слов (примерно): {words}")
    
    # Выводим первые 1500 символов извлеченного текста
    print("\nПервые 1500 символов текста:")
    print("-" * 80)
    print(text[:1500])
    print("-" * 80)
    
    # Сохраняем весь извлеченный текст в файл
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file = os.path.join(output_dir, "extracted_text.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    
    print(f"\nВесь извлеченный текст сохранен в файл: {output_file}")
    print("Для просмотра полного содержимого откройте этот файл в текстовом редакторе.")
    
    return True

if __name__ == "__main__":
    print("Тестирование извлечения текста из PDF файла")
    print("=" * 80)
    
    success = test_pdf_extraction()
    
    if success:
        print("\nТЕСТ ПРОЙДЕН: PDF файл успешно распознан и текст извлечен!")
        sys.exit(0)
    else:
        print("\nТЕСТ НЕ ПРОЙДЕН: Возникли проблемы при работе с PDF файлом.")
        sys.exit(1)
