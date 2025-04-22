import os
import re
from pathlib import Path

def load_env_vars():
    """Загружает переменные окружения из .env файла."""
    env_vars = {}
    env_path = Path(__file__).parent.parent / '.env'
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Пропускаем комментарии и пустые строки
                if not line or line.startswith('//') or line.startswith('#'):
                    continue
                
                # Разбираем строку формата key=value
                match = re.match(r'([^=]+)=(.*)', line)
                if match:
                    key, value = match.groups()
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

def get_env(key, default=None):
    """Получает значение переменной окружения из .env файла."""
    env_vars = load_env_vars()
    return env_vars.get(key, os.environ.get(key, default))
