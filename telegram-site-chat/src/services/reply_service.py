"""Сервис для работы с ответами администратора."""
from typing import List, Dict, Optional


class ReplyService:
    """Класс для управления ответами администратора."""
    
    def __init__(self):
        """Инициализация сервиса."""
        # Хранилище: site_chat_id -> список сообщений от админа
        self._pending_replies: Dict[str, List[str]] = {}
    
    def add_reply(self, site_chat_id: str, message: str) -> None:
        """
        Добавить ответ администратора для конкретного chat_id.
        
        Args:
            site_chat_id: ID чата на сайте
            message: Текст ответа
        """
        if site_chat_id not in self._pending_replies:
            self._pending_replies[site_chat_id] = []
        self._pending_replies[site_chat_id].append(message)
    
    def get_and_clear_replies(self, site_chat_id: str) -> List[str]:
        """
        Получить и очистить ответы для конкретного chat_id.
        
        Args:
            site_chat_id: ID чата на сайте
            
        Returns:
            Список ответов администратора
        """
        replies = self._pending_replies.pop(site_chat_id, [])
        return replies
    
    def has_replies(self, site_chat_id: str) -> bool:
        """
        Проверить наличие ответов для chat_id.
        
        Args:
            site_chat_id: ID чата на сайте
            
        Returns:
            True, если есть ответы, иначе False
        """
        return site_chat_id in self._pending_replies and len(self._pending_replies[site_chat_id]) > 0
    
    def initialize_chat(self, site_chat_id: str) -> None:
        """
        Инициализировать список ответов для нового chat_id.
        
        Args:
            site_chat_id: ID чата на сайте
        """
        if site_chat_id not in self._pending_replies:
            self._pending_replies[site_chat_id] = []
