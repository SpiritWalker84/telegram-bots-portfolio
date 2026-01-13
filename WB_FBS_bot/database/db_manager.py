"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
import logging
from typing import List, Optional
from contextlib import contextmanager


class DatabaseManager:
    """Класс для управления базой данных SQLite"""
    
    def __init__(self, db_path: str):
        """
        Инициализация менеджера базы данных
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """
        Контекстный менеджер для работы с подключением к БД
        
        Yields:
            sqlite3.Connection: Подключение к базе данных
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Ошибка при работе с БД: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        """Инициализация структуры базы данных"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_orders (
                    order_uid TEXT PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
            self.logger.info("База данных инициализирована")
    
    def is_order_processed(self, order_uid: str) -> bool:
        """
        Проверяет, был ли заказ уже обработан
        
        Args:
            order_uid: Уникальный идентификатор заказа
            
        Returns:
            bool: True если заказ уже обработан, False иначе
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM processed_orders WHERE order_uid = ?",
                (order_uid,)
            )
            return cursor.fetchone() is not None
    
    def mark_order_as_processed(self, order_uid: str, order_id: int, created_at: str) -> None:
        """
        Помечает заказ как обработанный
        
        Args:
            order_uid: Уникальный идентификатор заказа
            order_id: ID заказа
            created_at: Дата создания заказа
        """
        import datetime
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            processed_at = datetime.datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO processed_orders 
                (order_uid, order_id, created_at, processed_at)
                VALUES (?, ?, ?, ?)
            """, (order_uid, order_id, created_at, processed_at))
            conn.commit()
            self.logger.debug(f"Заказ {order_uid} помечен как обработанный")
    
    def get_processed_orders_count(self) -> int:
        """
        Возвращает количество обработанных заказов
        
        Returns:
            int: Количество обработанных заказов
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM processed_orders")
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def cleanup_old_orders(self, days: int = 30) -> int:
        """
        Удаляет старые записи о заказах
        
        Args:
            days: Количество дней, после которых записи считаются старыми
            
        Returns:
            int: Количество удаленных записей
        """
        import datetime
        
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM processed_orders WHERE processed_at < ?",
                (cutoff_date,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            self.logger.info(f"Удалено {deleted_count} старых записей")
            return deleted_count
    
    def get_setting(self, key: str) -> Optional[str]:
        """
        Получает значение настройки из БД
        
        Args:
            key: Ключ настройки
            
        Returns:
            Optional[str]: Значение настройки или None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM bot_settings WHERE key = ?",
                (key,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_setting(self, key: str, value: str) -> None:
        """
        Устанавливает значение настройки в БД
        
        Args:
            key: Ключ настройки
            value: Значение настройки
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_settings (key, value)
                VALUES (?, ?)
            """, (key, value))
            conn.commit()
            self.logger.debug(f"Настройка {key} сохранена")
    
    def get_orders_count_for_date(self, date: str) -> int:
        """
        Возвращает количество заказов, обработанных за указанную дату
        
        Args:
            date: Дата в формате YYYY-MM-DD или 'today' для сегодняшней даты
            
        Returns:
            int: Количество заказов за дату
        """
        import datetime
        
        if date == 'today':
            target_date = datetime.datetime.utcnow().date()
        else:
            target_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        
        start_datetime = datetime.datetime.combine(target_date, datetime.time.min).isoformat()
        end_datetime = datetime.datetime.combine(target_date, datetime.time.max).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM processed_orders 
                WHERE processed_at >= ? AND processed_at <= ?
            """, (start_datetime, end_datetime))
            result = cursor.fetchone()
            return result[0] if result else 0
