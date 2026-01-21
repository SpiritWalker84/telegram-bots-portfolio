"""Конфигурация бота с использованием ООП подхода."""
import os
import sys
import io
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Класс для управления конфигурацией бота."""
    
    def __init__(self):
        """Инициализация конфигурации с загрузкой переменных окружения."""
        # Устанавливаем UTF-8 для вывода в консоль Windows
        if sys.platform == 'win32':
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True
            )
        
        # Загружаем переменные окружения
        try:
            load_dotenv(encoding='utf-8')
        except Exception as e:
            print(f"Предупреждение: ошибка при загрузке .env файла: {e}")
        
        # Загружаем обязательные параметры
        self.bot_token: str = self._get_bot_token()
        self.db_name: str = os.getenv("DB_NAME", "tasks.db")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_file: Optional[str] = os.getenv("LOG_FILE")
    
    def _get_bot_token(self) -> str:
        """Получает токен бота из переменных окружения."""
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token or bot_token == "your_bot_token_here":
            raise ValueError(
                "BOT_TOKEN не найден в .env файле!\n"
                "Создайте файл .env и добавьте в него:\n"
                "BOT_TOKEN=ваш_токен_от_BotFather"
            )
        return bot_token
