"""Helper functions for booking bot."""
import logging
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False) -> None:
    """
    Безопасный ответ на callback_query с обработкой ошибок.
    
    Игнорирует ошибки "query is too old" и другие ошибки при остановке бота.
    
    Args:
        callback: CallbackQuery объект
        text: Текст для ответа (опционально)
        show_alert: Показывать ли alert (по умолчанию False)
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as e:
        # Игнорируем ошибки "query is too old" - это нормально при остановке бота
        if "query is too old" in str(e).lower() or "query id is invalid" in str(e).lower():
            logger.debug(f"Ignoring old callback query: {e}")
        else:
            logger.warning(f"Error answering callback query: {e}")
    except Exception as e:
        # Игнорируем другие ошибки при остановке (например, если сессия уже закрыта)
        logger.debug(f"Error answering callback query (likely during shutdown): {e}")


def get_status_ru(status: str) -> str:
    """Перевод статуса на русский язык"""
    status_map = {
        "pending": "ожидает",
        "confirmed": "подтверждена",
        "cancelled": "отменена"
    }
    return status_map.get(status, status)


def get_status_emoji(status: str) -> str:
    """Получить эмодзи для статуса"""
    status_map = {
        "pending": "⏳",
        "confirmed": "✅",
        "cancelled": "❌"
    }
    return status_map.get(status, "❓")
