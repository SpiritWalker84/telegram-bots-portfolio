"""
Inline-кнопки и календарь для бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from typing import List, Optional
import calendar


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Записаться", callback_data="book_appointment"),
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Услуги", callback_data="view_services"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ])
    return keyboard


def get_services_keyboard(services: List[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора услуги"""
    buttons = []
    for service in services:
        text = f"{service['name']}"
        # Добавляем длительность услуги
        if service.get('duration'):
            text += f" ({service['duration']} мин.)"
        if service.get('price'):
            text += f" - {service['price']:.0f}₽"
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"service_{service['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_calendar_keyboard(year: int, month: int, selected_date: Optional[str] = None) -> InlineKeyboardMarkup:
    """Календарь для выбора даты"""
    today = datetime.now().date()
    first_day = datetime(year, month, 1).date()
    
    # Заголовок календаря
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}"
    
    # Определяем день недели первого дня месяца (0 = понедельник)
    first_weekday = first_day.weekday()
    
    # Получаем количество дней в месяце
    days_in_month = calendar.monthrange(year, month)[1]
    
    keyboard = []
    
    # Кнопки навигации
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
    
    nav_buttons = [
        InlineKeyboardButton(text="◀️", callback_data=f"calendar_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text=header, callback_data="calendar_ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"calendar_{next_year}_{next_month}")
    ]
    keyboard.append(nav_buttons)
    
    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekday_buttons = [
        InlineKeyboardButton(text=day, callback_data="calendar_ignore")
        for day in weekdays
    ]
    keyboard.append(weekday_buttons)
    
    # Дни месяца
    current_date = first_day
    week = []
    
    # Пустые ячейки до первого дня
    for _ in range(first_weekday):
        week.append(InlineKeyboardButton(text=" ", callback_data="calendar_ignore"))
    
    # Дни месяца
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        current_date = datetime(year, month, day).date()
        
        # Проверяем, не прошедшая ли дата
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
    
    # Заполняем оставшиеся ячейки
    while len(week) < 7:
        week.append(InlineKeyboardButton(text=" ", callback_data="calendar_ignore"))
    if week:
        keyboard.append(week)
    
    # Кнопки быстрого выбора
    quick_buttons = []
    tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    after_tomorrow = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    
    quick_buttons.append(InlineKeyboardButton(
        text="Сегодня" if today.strftime("%Y-%m-%d") != selected_date else "[Сегодня]",
        callback_data=f"date_{today.strftime('%Y-%m-%d')}"
    ))
    quick_buttons.append(InlineKeyboardButton(
        text="Завтра",
        callback_data=f"date_{tomorrow}"
    ))
    quick_buttons.append(InlineKeyboardButton(
        text="Послезавтра",
        callback_data=f"date_{after_tomorrow}"
    ))
    keyboard.append(quick_buttons)
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_services")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_times_keyboard(times: List[dict], selected_time: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени
    
    Args:
        times: Список словарей с ключами 'time' (str) и 'available' (bool) или список строк (для обратной совместимости)
        selected_time: Выбранное время (опционально)
    """
    buttons = []
    row = []
    
    for time_info in times:
        # Поддержка обратной совместимости: если передан список строк
        if isinstance(time_info, str):
            time_str = time_info
            is_available = True
            is_past = False
        else:
            time_str = time_info.get("time", "")
            is_available = time_info.get("available", True)
            is_past = time_info.get("is_past", False)
        
        # Формируем текст кнопки с визуальным выделением
        if is_past:
            text = f"⏰ {time_str}"  # Прошедшее время (часы)
        elif not is_available:
            text = f"❌ {time_str}"  # Занятое время (с крестиком)
        else:
            text = time_str  # Доступное время (обычный текст)
        
        if selected_time == time_str:
            text = f"[{text}]"
        
        # Для занятых и прошедших времен используем специальный callback
        if not is_available or is_past:
            callback_data = f"time_busy_{time_str}"
        else:
            callback_data = f"time_{time_str}"
        
        row.append(InlineKeyboardButton(
            text=text,
            callback_data=callback_data
        ))
        
        if len(row) == 3:  # 3 кнопки в ряд
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_calendar")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard(appointment_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")
        ]
    ])
    return keyboard


def get_appointment_keyboard(appointment_id: int, can_cancel: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для записи"""
    buttons = []
    if can_cancel:
        buttons.append([
            InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_appointment_{appointment_id}")
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="my_appointments")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура администратора"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📅 Записи на сегодня", callback_data="admin_today")
        ],
        [
            InlineKeyboardButton(text="📆 Записи по дате", callback_data="admin_date_select")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить услугу", callback_data="admin_add_service"),
            InlineKeyboardButton(text="📋 Список услуг", callback_data="admin_services")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton(text="👥 Администраторы", callback_data="admin_list")
        ],
        [
            InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_admin_calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    """Календарь для администратора (выбор даты для просмотра записей)"""
    # Используем существующий календарь, но модифицируем callback_data
    base_calendar = get_calendar_keyboard(year, month)
    
    # Модифицируем все кнопки дат, чтобы они использовали префикс admin_date_
    modified_keyboard = []
    for row in base_calendar.inline_keyboard:
        modified_row = []
        for button in row:
            if button.callback_data:
                if button.callback_data.startswith("date_"):
                    # Заменяем "date_" на "admin_date_"
                    new_callback = button.callback_data.replace("date_", "admin_date_", 1)
                    modified_row.append(InlineKeyboardButton(
                        text=button.text,
                        callback_data=new_callback
                    ))
                elif button.callback_data == "back_to_services":
                    # Заменяем кнопку "Назад" на правильную для админа
                    modified_row.append(InlineKeyboardButton(
                        text="◀️ Назад",
                        callback_data="admin_panel"
                    ))
                else:
                    # Оставляем остальные кнопки как есть (навигация календаря и т.д.)
                    modified_row.append(button)
            else:
                modified_row.append(button)
        modified_keyboard.append(modified_row)
    
    return InlineKeyboardMarkup(inline_keyboard=modified_keyboard)


def get_back_keyboard(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Простая кнопка "Назад" """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])

