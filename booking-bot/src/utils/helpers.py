"""Helper functions for booking bot."""


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
