"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
import logging
import os
import time
from typing import List, Optional, Callable, TypeVar, Any
from contextlib import contextmanager
from functools import wraps

T = TypeVar('T')


def retry_db_operation(max_retries: int = 3, delay: float = 0.1, backoff: float = 2.0):
    """
    Декоратор для повторных попыток операций с БД при временных блокировках
    
    Args:
        max_retries: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель для увеличения задержки
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except sqlite3.OperationalError as e:
                    # Проверяем, является ли это временной блокировкой
                    error_msg = str(e).lower()
                    is_temporary = (
                        'locked' in error_msg or 
                        'database is locked' in error_msg or
                        ('unable to open database file' in error_msg and attempt < max_retries - 1)
                    )
                    
                    if is_temporary:
                        last_exception = e
                        if attempt < max_retries - 1:
                            self.logger.debug(
                                f"Временная ошибка БД при {func.__name__}: {e}, "
                                f"попытка {attempt + 1}/{max_retries}, ждем {current_delay:.2f}с"
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue
                    # Если это не временная блокировка или попытки исчерпаны, пробрасываем ошибку дальше
                    raise
                except Exception as e:
                    # Для других ошибок не делаем retry
                    raise
            
            # Если все попытки исчерпаны, пробрасываем последнюю ошибку
            if last_exception:
                self.logger.warning(
                    f"Не удалось выполнить {func.__name__} после {max_retries} попыток: {last_exception}"
                )
                raise last_exception
            
        return wrapper
    return decorator


class DatabaseManager:
    """Класс для управления базой данных SQLite"""
    
    def __init__(self, db_path: str):
        """
        Инициализация менеджера базы данных
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.logger = logging.getLogger(__name__)
        # Нормализуем путь: делаем абсолютным и создаем директорию, если нужно
        self.logger.debug(f"Исходный путь к БД: {db_path} (абсолютный: {os.path.isabs(db_path)})")
        self.db_path = self._normalize_db_path(db_path)
        self.logger.info(f"Используется база данных: {self.db_path}")
        self._init_database()
    
    def _normalize_db_path(self, db_path: str) -> str:
        """
        Нормализует путь к базе данных: делает абсолютным и создает директорию
        
        Args:
            db_path: Исходный путь к БД
            
        Returns:
            str: Абсолютный путь к БД
        """
        # Если путь уже абсолютный, используем его как есть
        if os.path.isabs(db_path):
            abs_path = db_path
        else:
            # Определяем директорию проекта относительно расположения этого файла
            # Структура: WB_FBS_bot/database/db_manager.py -> проект на 2 уровня выше
            current_file = os.path.abspath(__file__)
            project_dir = os.path.dirname(os.path.dirname(current_file))
            # Делаем путь абсолютным относительно директории проекта
            abs_path = os.path.join(project_dir, db_path)
            # Нормализуем путь (убираем .., . и т.д.)
            abs_path = os.path.normpath(abs_path)
        
        # Получаем директорию для файла БД
        db_dir = os.path.dirname(abs_path)
        
        # Если директория пустая (файл в корне), используем директорию проекта
        if not db_dir:
            current_file = os.path.abspath(__file__)
            project_dir = os.path.dirname(os.path.dirname(current_file))
            db_dir = project_dir
            abs_path = os.path.join(db_dir, os.path.basename(db_path))
        
        # Создаем директорию, если её нет
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, mode=0o755, exist_ok=True)
                self.logger.info(f"Создана директория для базы данных: {db_dir}")
            except OSError as e:
                self.logger.error(f"Не удалось создать директорию {db_dir}: {e}")
                raise
        
        # Проверяем права на запись в директорию
        if db_dir and os.path.exists(db_dir):
            if not os.access(db_dir, os.W_OK):
                error_msg = f"Нет прав на запись в директорию {db_dir}"
                self.logger.error(error_msg)
                raise PermissionError(error_msg)
        
        self.logger.debug(f"Нормализованный путь к БД: {abs_path}, директория: {db_dir}")
        return abs_path
    
    @contextmanager
    def _get_connection(self):
        """
        Контекстный менеджер для работы с подключением к БД
        
        Yields:
            sqlite3.Connection: Подключение к базе данных
        """
        conn = None
        try:
            # Проверяем, что директория существует и доступна для записи
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                error_msg = f"Директория {db_dir} не существует"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            if db_dir and not os.access(db_dir, os.W_OK):
                error_msg = f"Нет прав на запись в директорию {db_dir}"
                self.logger.error(error_msg)
                raise PermissionError(error_msg)
            
            # Пытаемся подключиться к БД с увеличенным timeout для конкурентного доступа
            self.logger.debug(f"Подключение к базе данных: {self.db_path}")
            conn = sqlite3.connect(self.db_path, timeout=20.0)
            conn.row_factory = sqlite3.Row
            self.logger.debug("Подключение к базе данных установлено")
        except sqlite3.OperationalError as e:
            error_str = str(e).lower()
            # Проверяем, является ли это временной блокировкой
            if 'locked' in error_str or 'database is locked' in error_str:
                # Временная блокировка - пробрасываем как есть для retry
                self.logger.debug(f"Временная блокировка БД: {e}")
                raise
            # Постоянная ошибка (например, unable to open database file)
            error_msg = (
                f"Не удалось открыть базу данных {self.db_path}: {e}. "
                f"Проверьте права доступа к файлу и директории {db_dir if db_dir else 'текущей'}. "
                f"Абсолютный путь: {os.path.abspath(self.db_path)}"
            )
            self.logger.error(error_msg)
            raise
        except (FileNotFoundError, PermissionError) as e:
            self.logger.error(f"Ошибка доступа к БД: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при подключении к БД: {e}", exc_info=True)
            raise
        
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
    
    @retry_db_operation(max_retries=3, delay=0.1, backoff=2.0)
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
    
    @retry_db_operation(max_retries=3, delay=0.1, backoff=2.0)
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
