"""Утилиты для парсинга данных."""
import re
from typing import Optional


class ChatIdParser:
    """Класс для извлечения chat_id из сообщений."""
    
    @staticmethod
    def extract_site_chat_id(text: str) -> Optional[str]:
        """
        Извлечь site_chat_id из текста сообщения.
        
        Args:
            text: Текст сообщения
            
        Returns:
            site_chat_id или None, если не найден
        """
        if not text:
            return None
            
        # Ищем паттерн вида "chat_id: chat_xxx"
        match = re.search(r'chat_id:\s*([a-zA-Z0-9_]+)', text)
        return match.group(1) if match else None
