"""
Inline keyboards and calendars for booking-bot.

Moved from root-level `keyboards.py` during refactor.
"""

import calendar
from datetime import datetime, timedelta
from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Записаться", callback_data="book_appointment"),
                InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Услуги", callback_data="view_services"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            ],
        ]
    )
    return keyboard


def get_services_keyboard(services: List[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора услуги"""
    buttons = []
    for service in services:
        text = f"{service['name']}"
        if service.get("duration"):
            text += f" ({service['duration']} мин.)"
        if service.get("price"):
            text += f" - {service['price']:.0f}₽"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"service_{service['id']}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_calendar_keyboard(year: int, month: int, selected_date: Optional[str] = None) -> InlineKeyboardMarkup:
    """Календарь для выбора даты"""
    today = datetime.now().date()
    first_day = datetime(year, month, 1).date()

    month_name = calendar.month_name[month]
    header = f"{month_name} {year}"

    first_weekday = first_day.weekday()  # 0 = понедельник
    days_in_month = calendar.monthrange(year, month)[1]

    keyboard: List[List[InlineKeyboardButton]] = []

    # Навигация
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1

    keyboard.append(
        [
            InlineKeyboardButton(text="◀️", callback_data=f"calendar_{prev_year}_{prev_month}"),
            InlineKeyboardButton(text=header, callback_data="calendar_ignore"),
            InlineKeyboardButton(text="▶️", callback_data=f"calendar_{next_year}_{next_month}"),
        ]
    )

    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(text=day, callback_data="calendar_ignore") for day in weekdays])

    week: List[InlineKeyboardButton] = []
    for _ in range(first_weekday):
        week.append(InlineKeyboardButton(text=" ", callback_data="calendar_ignore"))

    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        current_date = datetime(year, month, day).date()

        if current_date < today:
            text = " "
            callback = "calendar_ignore"
        else:
            text = str(day)
            if selected_date == date_str:
                text = f"[{day}]"
            callback = f"date_{date_str}"

        week.append(InlineKeyboardButton(text=text, callback_data=callback))
        if len(week) == 7:
            keyboard.append(week)
            week = []

    while len(week) < 7:
        week.append(InlineKeyboardButton(text=" ", callback_data="calendar_ignore"))
    if week:
        keyboard.append(week)

    # Быстрый выбор
    tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    after_tomorrow = (today + timedelta(days=2)).strftime("%Y-%m-%d")

    keyboard.append(
        [
            InlineKeyboardButton(
                text="Сегодня" if today.strftime("%Y-%m-%d") != selected_date else "[Сегодня]",
                callback_data=f"date_{today.strftime('%Y-%m-%d')}",
            ),
            InlineKeyboardButton(text="Завтра", callback_data=f"date_{tomorrow}"),
            InlineKeyboardButton(text="Послезавтра", callback_data=f"date_{after_tomorrow}"),
        ]
    )

    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_services")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_times_keyboard(times: List[dict], selected_time: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени.

    Args:
        times: список dict с ключами 'time' (str) и 'available' (bool) или список строк (совместимость)
        selected_time: выбранное время
    """
    buttons: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []

    for time_info in times:
        if isinstance(time_info, str):
            time_str = time_info
            is_available = True
            is_past = False
        else:
            time_str = time_info.get("time", "")
            is_available = time_info.get("available", True)
            is_past = time_info.get("is_past", False)

        if is_past:
            text = f"⏰ {time_str}"
        elif not is_available:
            text = f"❌ {time_str}"
        else:
            text = time_str

        if selected_time == time_str:
            text = f"[{text}]"

        if not is_available or is_past:
            callback_data = f"time_busy_{time_str}"
        else:
            callback_data = f"time_{time_str}"

        row.append(InlineKeyboardButton(text=text, callback_data=callback_data))

        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_calendar")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard(appointment_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking"),
            ]
        ]
    )
    return keyboard


def get_appointment_keyboard(appointment_id: int, can_cancel: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для записи"""
    buttons: List[List[InlineKeyboardButton]] = []
    if can_cancel:
        buttons.append(
            [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_appointment_{appointment_id}")]
        )
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_appointments")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура администратора"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="📅 Записи на сегодня", callback_data="admin_today"),
            ],
            [InlineKeyboardButton(text="📆 Записи по дате", callback_data="admin_date_select")],
            [
                InlineKeyboardButton(text="➕ Добавить услугу", callback_data="admin_add_service"),
                InlineKeyboardButton(text="📋 Список услуг", callback_data="admin_services"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
                InlineKeyboardButton(text="👥 Администраторы", callback_data="admin_list"),
            ],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
        ]
    )
    return keyboard


def get_admin_calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    """Календарь для администратора (выбор даты для просмотра записей)."""
    base_calendar = get_calendar_keyboard(year, month)

    modified_keyboard: List[List[InlineKeyboardButton]] = []
    for row in base_calendar.inline_keyboard:
        modified_row: List[InlineKeyboardButton] = []
        for button in row:
            if button.callback_data:
                if button.callback_data.startswith("date_"):
                    new_callback = button.callback_data.replace("date_", "admin_date_", 1)
                    modified_row.append(
                        InlineKeyboardButton(
                            text=button.text,
                            callback_data=new_callback,
                        )
                    )
                elif button.callback_data == "back_to_services":
                    modified_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel"))
                else:
                    modified_row.append(button)
            else:
                modified_row.append(button)
        modified_keyboard.append(modified_row)

    return InlineKeyboardMarkup(inline_keyboard=modified_keyboard)


def get_back_keyboard(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Простая кнопка 'Назад'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]]
    )

