import os
from pypdf import PdfReader
import docx

def extract_text(file_path):
    """Извлекает текст из файла (PDF, DOCX, TXT)."""
    _, file_extension = os.path.splitext(file_path)
    text = ""

    try:
        if file_extension.lower() == '.pdf':
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif file_extension.lower() == '.docx':
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file_extension.lower() == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            print(f"Предупреждение: Неподдерживаемый тип файла: {file_extension}")
            return None
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден: {file_path}")
        return None
    except Exception as e:
        print(f"Ошибка при обработке файла {file_path}: {e}")
        return None

    return text
