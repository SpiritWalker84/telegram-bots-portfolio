"""Модели данных и класс для работы с базой данных."""
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """Класс для работы с базой данных SQLite."""
    
    def __init__(self, db_name: str):
        """
        Инициализация подключения к базе данных.
        
        Args:
            db_name: Путь к файлу базы данных
        """
        self.db_name = db_name
    
    async def init_db(self) -> None:
        """Создаёт таблицы tasks и user_settings, если их нет."""
        async with aiosqlite.connect(self.db_name) as db:
            # Таблица задач
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    datetime TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME
                )
            """)
            
            # Таблица настроек пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    auto_delete_days INTEGER DEFAULT 1
                )
            """)
            
            # Добавляем поле completed_at, если его нет (для существующих баз)
            try:
                await db.execute("ALTER TABLE tasks ADD COLUMN completed_at DATETIME")
            except aiosqlite.OperationalError:
                pass  # Поле уже существует
            
            await db.commit()
    
    async def add_task(
        self, 
        user_id: int, 
        text: str, 
        reminder_time: Optional[datetime] = None
    ) -> int:
        """
        Добавляет задачу в базу данных. Возвращает ID задачи.
        
        Args:
            user_id: ID пользователя Telegram
            text: Текст задачи
            reminder_time: Время напоминания (если None, то через 1 час)
            
        Returns:
            ID созданной задачи
        """
        if reminder_time is None:
            reminder_time = datetime.now()
        
        dt_str = reminder_time.isoformat()
        
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, text, datetime, status) VALUES (?, ?, ?, ?)",
                (user_id, text, dt_str, "pending")
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_user_tasks(
        self, 
        user_id: int, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает задачи пользователя. Если status указан, фильтрует по статусу.
        
        Args:
            user_id: ID пользователя Telegram
            status: Статус задачи ('pending' или 'done'), или None для всех
            
        Returns:
            Список задач в виде словарей
        """
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            
            if status:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY datetime ASC",
                    (user_id, status)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM tasks WHERE user_id = ? ORDER BY datetime ASC",
                    (user_id,)
                )
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def mark_task_done(self, task_id: int, user_id: int) -> bool:
        """
        Отмечает задачу как выполненную. Возвращает True, если задача найдена.
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя Telegram
            
        Returns:
            True если задача найдена и обновлена, False иначе
        """
        now_str = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ? AND user_id = ?",
                (now_str, task_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """
        Удаляет задачу. Возвращает True, если задача найдена.
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя Telegram
            
        Returns:
            True если задача найдена и удалена, False иначе
        """
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "DELETE FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_user_setting(
        self, 
        user_id: int, 
        setting_name: str, 
        default_value: Any
    ) -> Any:
        """
        Получает настройку пользователя. Если не найдена, возвращает значение по умолчанию.
        
        Args:
            user_id: ID пользователя Telegram
            setting_name: Название настройки
            default_value: Значение по умолчанию
            
        Returns:
            Значение настройки или default_value
        """
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                f"SELECT {setting_name} FROM user_settings WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return row[0]
            return default_value
    
    async def set_user_setting(self, user_id: int, setting_name: str, value: Any) -> None:
        """
        Устанавливает настройку пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            setting_name: Название настройки
            value: Значение настройки
        """
        async with aiosqlite.connect(self.db_name) as db:
            # Проверяем, существует ли запись
            cursor = await db.execute(
                "SELECT user_id FROM user_settings WHERE user_id = ?",
                (user_id,)
            )
            exists = await cursor.fetchone()
            
            if exists:
                # Обновляем существующую запись
                await db.execute(
                    f"UPDATE user_settings SET {setting_name} = ? WHERE user_id = ?",
                    (value, user_id)
                )
            else:
                # Создаём новую запись
                await db.execute(
                    f"INSERT INTO user_settings (user_id, {setting_name}) VALUES (?, ?)",
                    (user_id, value)
                )
            await db.commit()
    
    async def get_pending_tasks_for_reminder(self) -> List[Dict[str, Any]]:
        """
        Получает все задачи со статусом 'pending', время которых уже наступило.
        
        Returns:
            Список задач, готовых для напоминания
        """
        now = datetime.now()
        now_str = now.isoformat()
        
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE status = 'pending' AND datetime <= ?",
                (now_str,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def remove_expired_tasks(self) -> None:
        """Удаляет истёкшие задачи с учётом индивидуальных настроек пользователей."""
        from datetime import timedelta
        
        now = datetime.now()
        
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            
            # Получаем все выполненные задачи
            cursor = await db.execute(
                "SELECT id, user_id, completed_at FROM tasks WHERE status = 'done' AND completed_at IS NOT NULL"
            )
            done_tasks = await cursor.fetchall()
            
            # Удаляем выполненные задачи, которые истекли по настройкам пользователя
            for task in done_tasks:
                user_id = task["user_id"]
                completed_at_str = task["completed_at"]
                
                try:
                    completed_at = datetime.fromisoformat(completed_at_str)
                    auto_delete_days = await self.get_user_setting(user_id, "auto_delete_days", 1)
                    expired_time = completed_at + timedelta(days=auto_delete_days)
                    
                    if now >= expired_time:
                        await db.execute("DELETE FROM tasks WHERE id = ?", (task["id"],))
                except (ValueError, TypeError):
                    # Если дата в неверном формате, пропускаем
                    continue
            
            # Удаляем просроченные задачи (более 24 часов с момента напоминания)
            expired_time = now - timedelta(hours=24)
            expired_str = expired_time.isoformat()
            await db.execute(
                "DELETE FROM tasks WHERE status = 'pending' AND datetime < ?",
                (expired_str,)
            )
            
            await db.commit()
