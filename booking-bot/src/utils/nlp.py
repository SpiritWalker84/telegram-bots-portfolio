"""Natural language parsing helpers (date/time)."""

import re
from datetime import datetime, timedelta
from typing import Optional

from dateutil import parser as date_parser


def parse_natural_date(text: str) -> Optional[str]:
    """Parse date from natural language; returns YYYY-MM-DD or None."""
    text = text.lower().strip()
    today = datetime.now().date()

    # Сегодня
    if any(word in text for word in ["сегодня", "today"]):
        return today.strftime("%Y-%m-%d")

    # Завтра
    if any(word in text for word in ["завтра", "tomorrow"]):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    # Послезавтра
    if any(word in text for word in ["послезавтра", "day after tomorrow"]):
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")

    # Через N дней
    match = re.search(r"через\s+(\d+)", text)
    if match:
        days = int(match.group(1))
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")

    # Парсинг даты через dateutil
    try:
        parsed_date = date_parser.parse(text, fuzzy=True, dayfirst=True)
        if parsed_date:
            return parsed_date.date().strftime("%Y-%m-%d")
    except Exception:
        pass

    # Формат DD.MM или DD.MM.YYYY
    match = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", text)
    if match:
        day, month, year = match.groups()
        year = int(year) if year else today.year
        try:
            date_obj = datetime(int(year), int(month), int(day)).date()
            if date_obj >= today:
                return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def parse_natural_time(text: str) -> Optional[str]:
    """Parse time from natural language; returns HH:MM or None."""
    text = text.lower().strip()

    # Формат HH:MM
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"

    # Формат HH MM (без двоеточия)
    match = re.search(r"(\d{1,2})\s+(\d{2})", text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"

    # Только час (например, "15" или "3 часа")
    match = re.search(r"(\d{1,2})(?:\s*(?:час|часа|часов|h|hours?))?", text)
    if match:
        hour = int(match.group(1))
        if 0 <= hour < 24:
            return f"{hour:02d}:00"

    return None

