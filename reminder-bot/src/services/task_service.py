"""Сервис для работы с задачами."""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from src.database.models import Database
from src.utils.parsers import TimeParser


class TaskService:
    """Сервис для бизнес-логики работы с задачами."""
    
    def __init__(self, database: Database):
        """
        Инициализация сервиса задач.
        
        Args:
            database: Экземпляр класса Database
        """
        self.db = database
        self.time_parser = TimeParser()
    
    async def add_task(
        self, 
        user_id: int, 
        text: str, 
        reminder_time: Optional[datetime] = None
    ) -> int:
        """
        Добавляет задачу. Если время не указано, парсит из текста или устанавливает через 1 час.
        
        Args:
            user_id: ID пользователя Telegram
            text: Текст задачи (может содержать время)
            reminder_time: Время напоминания (если None, парсится из text или устанавливается через 1 час)
            
        Returns:
            ID созданной задачи
        """
        # Если время не указано, пытаемся распарсить из текста
        if reminder_time is None:
            parsed_time, cleaned_text = self.time_parser.parse_time_from_text(text)
            reminder_time = parsed_time
            text = cleaned_text
            
            # Если парсинг не удался, устанавливаем через 1 час
            if reminder_time is None:
                reminder_time = datetime.now() + timedelta(hours=1)
        
        return await self.db.add_task(user_id, text, reminder_time)
    
    async def get_user_tasks(
        self, 
        user_id: int, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает задачи пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            status: Статус задачи ('pending' или 'done'), или None для всех
            
        Returns:
            Список задач
        """
        return await self.db.get_user_tasks(user_id, status)
    
    async def mark_task_done(self, task_id: int, user_id: int) -> bool:
        """
        Отмечает задачу как выполненную.
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя Telegram
            
        Returns:
            True если задача найдена и обновлена
        """
        return await self.db.mark_task_done(task_id, user_id)
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """
        Удаляет задачу.
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя Telegram
            
        Returns:
            True если задача найдена и удалена
        """
        return await self.db.delete_task(task_id, user_id)
