"""Утилита для retry-логики при сетевых ошибках Telegram."""
import asyncio
import logging
from typing import TypeVar, Callable, Awaitable, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_send_message(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 2.0,
    error_message: str = "Ошибка при отправке сообщения",
) -> T | None:
    """
    Retry-логика для отправки сообщений.
    
    Args:
        func: Асинхронная функция для выполнения
        max_attempts: Максимальное количество попыток (по умолчанию 3)
        delay: Задержка между попытками в секундах (по умолчанию 2.0)
        error_message: Сообщение об ошибке для логирования
    
    Returns:
        Результат выполнения функции или None при неудаче
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                logger.warning(
                    f"{error_message} (попытка {attempt}/{max_attempts}): {e}. "
                    f"Повтор через {delay} сек..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"{error_message} после {max_attempts} попыток: {e}")
    
    return None


async def retry_send_statistics(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 5.0,
    error_message: str = "Ошибка при отправке статистики",
) -> T | None:
    """
    Retry-логика для отправки статистики.
    
    Args:
        func: Асинхронная функция для выполнения
        max_attempts: Максимальное количество попыток (по умолчанию 3)
        delay: Задержка между попытками в секундах (по умолчанию 5.0)
        error_message: Сообщение об ошибке для логирования
    
    Returns:
        Результат выполнения функции или None при неудаче
    """
    return await retry_send_message(func, max_attempts, delay, error_message)
