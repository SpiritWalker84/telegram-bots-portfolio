"""
Утилиты для обработки текста и данных.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def truncate_text(text: str, max_length: int = 60) -> str:
    """
    Обрезает текст до максимальной длины с добавлением многоточия.

    Args:
        text: Исходный текст
        max_length: Максимальная длина (по умолчанию 60)

    Returns:
        Обрезанный текст с "..." если превышает max_length
    """
    if not isinstance(text, str):
        text = str(text)
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Безопасное преобразование значения в float.

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию при ошибке

    Returns:
        float значение или default
    """
    if value is None:
        return default
    
    try:
        # Убираем пробелы и заменяем запятую на точку
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Не удалось преобразовать '{value}' в float, используется {default}")
        return default


def safe_str(value: Any, default: str = "") -> str:
    """
    Безопасное преобразование значения в строку.

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию при ошибке

    Returns:
        str значение или default
    """
    if value is None:
        return default
    
    try:
        return str(value).strip()
    except (ValueError, TypeError):
        logger.warning(f"Не удалось преобразовать '{value}' в str, используется '{default}'")
        return default




