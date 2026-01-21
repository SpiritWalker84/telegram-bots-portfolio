"""Сервис для отправки напоминаний."""
import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from aiogram import Bot
    from src.database.models import Database


class ReminderService:
    """Сервис для фоновой отправки напоминаний."""
    
    def __init__(self, bot: "Bot", database: "Database"):
        """
        Инициализация сервиса напоминаний.
        
        Args:
            bot: Экземпляр бота aiogram
            database: Экземпляр класса Database
        """
        self.bot = bot
        self.db = database
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def start(self) -> None:
        """Запускает фоновый цикл для проверки и отправки напоминаний."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._reminder_loop())
    
    async def stop(self) -> None:
        """Останавливает фоновый цикл."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _reminder_loop(self) -> None:
        """Фоновый цикл для проверки и отправки напоминаний."""
        while self._running:
            try:
                await self._send_reminders()
                await self.db.remove_expired_tasks()
            except Exception as e:
                print(f"Ошибка в reminder_loop: {e}")
            
            await asyncio.sleep(60)  # Проверка каждые 60 секунд
    
    async def _send_reminders(self) -> None:
        """Отправляет напоминания пользователям о задачах, время которых наступило."""
        tasks = await self.db.get_pending_tasks_for_reminder()
        
        for task in tasks:
            user_id = task["user_id"]
            task_text = task["text"]
            task_id = task["id"]
            
            try:
                message = f"🔔 Напоминание!\n\nЗадача #{task_id}: {task_text}"
                await self.bot.send_message(chat_id=user_id, text=message)
                
                # Отмечаем задачу как выполненную после отправки напоминания
                await self.db.mark_task_done(task_id, user_id)
            except Exception as e:
                print(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
