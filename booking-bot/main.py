"""
Основной файл Telegram Booking Bot
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dateutil import parser as date_parser

import config
from database import Database
from keyboards import (
    get_main_menu, get_services_keyboard, get_calendar_keyboard,
    get_times_keyboard, get_confirm_keyboard, get_appointment_keyboard,
    get_admin_keyboard, get_back_keyboard, get_admin_calendar_keyboard
)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database(config.DB_PATH)


# ========== Вспомогательные функции ==========

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


# Состояния FSM
class BookingStates(StatesGroup):
    waiting_for_service = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_notes = State()
    waiting_for_confirmation = State()


class AdminStates(StatesGroup):
    adding_service_name = State()
    adding_service_duration = State()
    adding_service_price = State()
    adding_service_description = State()
    editing_service_value = State()
    setting_working_hours_start = State()
    setting_working_hours_end = State()
    setting_appointment_interval = State()


# ========== Парсинг естественного языка ==========

def parse_natural_date(text: str) -> Optional[str]:
    """Парсинг даты из естественного языка"""
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
    match = re.search(r'через\s+(\d+)', text)
    if match:
        days = int(match.group(1))
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")
    
    # Парсинг даты через dateutil
    try:
        parsed_date = date_parser.parse(text, fuzzy=True, dayfirst=True)
        if parsed_date:
            return parsed_date.date().strftime("%Y-%m-%d")
    except:
        pass
    
    # Формат DD.MM или DD.MM.YYYY
    match = re.search(r'(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?', text)
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
    """Парсинг времени из естественного языка"""
    text = text.lower().strip()
    
    # Формат HH:MM
    match = re.search(r'(\d{1,2}):(\d{2})', text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"
    
    # Формат HH MM (без двоеточия)
    match = re.search(r'(\d{1,2})\s+(\d{2})', text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return f"{hour:02d}:{minute:02d}"
    
    # Только час (например, "15" или "3 часа")
    match = re.search(r'(\d{1,2})(?:\s*(?:час|часа|часов|h|hours?))?', text)
    if match:
        hour = int(match.group(1))
        if 0 <= hour < 24:
            return f"{hour:02d}:00"
    
    return None


# ========== Команды ==========

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    user = message.from_user
    
    # Проверяем, является ли пользователь администратором
    is_admin = await db.is_admin(user.id) or user.id == config.ADMIN_ID
    
    text = f"👋 Привет, {user.first_name}!\n\n"
    text += "Я бот для записи на услуги.\n"
    text += "Выберите действие из меню:"
    
    keyboard = get_main_menu()
    if is_admin:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin_panel")
        ])
    
    await message.answer(text, reply_markup=keyboard)
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    text = """
📖 **Помощь по использованию бота**

**Основные команды:**
/start - Главное меню
/help - Эта справка
/cancel - Отменить текущее действие

**Как записаться:**
1. Нажмите "📅 Записаться"
2. Выберите услугу
3. Выберите дату (можно использовать календарь или написать "завтра")
4. Выберите время (можно написать "15:00" или "15")
5. Подтвердите запись

**Примеры записи:**
- "завтра 15:00"
- "послезавтра в 10"
- "25.12 в 14:30"

**Просмотр записей:**
Нажмите "📋 Мои записи" чтобы увидеть все ваши записи.
"""
    await message.answer(text, reply_markup=get_back_keyboard())


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu())


# ========== Обработчики callback ==========

@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню\n\nВыберите действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "book_appointment")
async def callback_book_appointment(callback: CallbackQuery, state: FSMContext):
    """Начало процесса записи"""
    services = await db.get_all_services(active_only=True)
    
    if not services:
        await callback.answer("❌ Нет доступных услуг", show_alert=True)
        return
    
    await state.set_state(BookingStates.waiting_for_service)
    await callback.message.edit_text(
        "📋 Выберите услугу:",
        reply_markup=get_services_keyboard(services)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("service_"))
async def callback_service_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор услуги"""
    service_id = int(callback.data.split("_")[1])
    service = await db.get_service(service_id)
    
    if not service or not service["is_active"]:
        await callback.answer("❌ Услуга недоступна", show_alert=True)
        return
    
    await state.update_data(service_id=service_id, service_name=service["name"])
    
    # Показываем календарь
    today = datetime.now().date()
    keyboard = get_calendar_keyboard(today.year, today.month)
    
    await state.set_state(BookingStates.waiting_for_date)
    await callback.message.edit_text(
        f"📅 Выберите дату для услуги: **{service['name']}**\n\n"
        f"Длительность: {service['duration']} мин.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_services")
async def callback_back_to_services(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору услуги"""
    await state.set_state(BookingStates.waiting_for_service)
    services = await db.get_all_services(active_only=True)
    
    if not services:
        await callback.answer("❌ Нет доступных услуг", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📋 Выберите услугу:",
        reply_markup=get_services_keyboard(services)
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_calendar")
async def callback_back_to_calendar(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    data = await state.get_data()
    service_id = data.get("service_id")
    service_name = data.get("service_name")
    
    if not service_id:
        await callback.answer("❌ Ошибка: услуга не выбрана", show_alert=True)
        return
    
    # Получаем информацию об услуге
    service = await db.get_service(service_id)
    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    # Обновляем данные в состоянии
    if not service_name:
        service_name = service["name"]
        await state.update_data(service_name=service_name)
    
    await state.set_state(BookingStates.waiting_for_date)
    today = datetime.now().date()
    keyboard = get_calendar_keyboard(today.year, today.month)
    
    await callback.message.edit_text(
        f"📅 Выберите дату для услуги: **{service_name}**\n\n"
        f"Длительность: {service['duration']} мин.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("calendar_"))
async def callback_calendar_nav(callback: CallbackQuery, state: FSMContext):
    """Навигация по календарю"""
    if callback.data == "calendar_ignore":
        await callback.answer()
        return
    
    parts = callback.data.split("_")
    year, month = int(parts[1]), int(parts[2])
    
    # Проверяем, используется ли календарь для админа
    # Если в сообщении есть "Выберите дату для просмотра записей", используем админ-календарь
    is_admin_calendar = False
    if callback.message.text:
        if "Выберите дату для просмотра записей" in callback.message.text:
            is_admin_calendar = True
    
    if is_admin_calendar:
        keyboard = get_admin_calendar_keyboard(year, month)
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")
        ])
        await callback.message.edit_text(
            "📆 **Выберите дату для просмотра записей:**",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        # Для обычного календаря нужно получить данные об услуге
        data = await state.get_data()
        service_id = data.get("service_id")
        service_name = data.get("service_name")
        
        if service_id:
            # Если есть услуга, показываем календарь с информацией об услуге
            keyboard = get_calendar_keyboard(year, month)
            service = await db.get_service(service_id)
            if not service_name and service:
                service_name = service["name"]
                await state.update_data(service_name=service_name)
            
            if service:
                await callback.message.edit_text(
                    f"📅 Выберите дату для услуги: **{service_name or service['name']}**\n\n"
                    f"Длительность: {service['duration']} мин.",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await callback.message.edit_reply_markup(reply_markup=keyboard)
        else:
            keyboard = get_calendar_keyboard(year, month)
            await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    await callback.answer()


@dp.callback_query(F.data == "admin_date_select")
async def callback_admin_date_select(callback: CallbackQuery):
    """Выбор даты для просмотра записей"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    # Показываем календарь для выбора даты
    today = datetime.now().date()
    keyboard = get_admin_calendar_keyboard(today.year, today.month)
    
    # Добавляем кнопку назад
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")
    ])
    
    await callback.message.edit_text(
        "📆 **Выберите дату для просмотра записей:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_date_"))
async def callback_admin_view_date(callback: CallbackQuery):
    """Просмотр записей на выбранную дату (админ)"""
    # Игнорируем admin_date_select - он обрабатывается отдельным обработчиком
    if callback.data == "admin_date_select":
        return
    
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    # Извлекаем дату из callback_data (формат: admin_date_YYYY-MM-DD)
    # Убираем префикс "admin_date_"
    date_str = callback.data.replace("admin_date_", "", 1)
    
    # Проверяем, что это действительно дата, а не навигация календаря
    # Дата должна быть в формате YYYY-MM-DD (10 символов, 2 дефиса)
    if not date_str or len(date_str) != 10 or date_str.count("-") != 2:
        # Если это не дата, возможно это навигация - игнорируем
        logger.warning(f"Некорректный формат даты в admin_date_: {callback.data}")
        await callback.answer()
        return
    
    # Проверяем, что это валидная дата
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Невалидная дата в admin_date_: {date_str}")
        await callback.answer()
        return
    
    logger.info(f"Админ {user_id} запросил записи на дату {date_str}")
    
    appointments = await db.get_appointments_by_date(date_str)
    logger.info(f"Найдено записей на {date_str}: {len(appointments) if appointments else 0}")
    
    if not appointments:
        text = f"📅 На {date_str} нет записей."
    else:
        text = f"📅 **Записи на {date_str}:**\n\n"
        for apt in appointments:
            status_emoji = get_status_emoji(apt["status"])
            status_ru = get_status_ru(apt["status"])
            
            text += f"{status_emoji} **#{apt['id']}** - {apt['service_name']}\n"
            text += f"   👤 {apt['client_name']}"
            if apt.get('client_username'):
                text += f" (@{apt['client_username']})"
            text += f"\n   ⏰ {apt['time']}\n"
            text += f"   Статус: {status_ru}\n"
            if apt.get('notes'):
                text += f"   📝 Примечание: {apt['notes']}\n"
            text += "\n"
    
    buttons = []
    
    # Добавляем кнопки управления для каждой записи
    if appointments:
        for apt in appointments:
            if apt["status"] != "cancelled":
                buttons.append([
                    InlineKeyboardButton(
                        text=f"✅ Подтвердить #{apt['id']}",
                        callback_data=f"admin_confirm_appt_{apt['id']}"
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Отменить #{apt['id']}",
                        callback_data=f"admin_cancel_appt_{apt['id']}"
                    )
                ])
    
    buttons.append([
        InlineKeyboardButton(text="📆 Выбрать другую дату", callback_data="admin_date_select"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("date_"))
async def callback_date_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор даты"""
    try:
        date_str = callback.data.split("_", 1)[1]
        
        # Проверяем формат даты (должно быть YYYY-MM-DD)
        if len(date_str) != 10 or date_str.count("-") != 2:
            await callback.answer()
            return
        
        data = await state.get_data()
        service_id = data.get("service_id")
        
        if not service_id:
            logger.warning(f"Попытка выбрать дату без выбранной услуги. User: {callback.from_user.id}, data: {callback.data}")
            await callback.answer("❌ Ошибка: услуга не выбрана. Начните запись заново.", show_alert=True)
            return
        
        # Проверяем, что дата не в прошлом
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if selected_date < datetime.now().date():
            await callback.answer("❌ Нельзя выбрать прошедшую дату", show_alert=True)
            return
        
        await state.update_data(date=date_str)
        
        # Получаем все времена с информацией о доступности
        times = await db.get_all_times_with_availability(date_str, service_id)
        
        if not times:
            await callback.answer("❌ Нет доступных времен на эту дату", show_alert=True)
            return
        
        # Проверяем, есть ли хотя бы одно доступное время
        available_count = sum(1 for t in times if t.get("available", False))
        if available_count == 0:
            await callback.answer("❌ Нет свободного времени на эту дату", show_alert=True)
            return
        
        keyboard = get_times_keyboard(times)
        await state.set_state(BookingStates.waiting_for_time)
        await callback.message.edit_text(
            f"⏰ Выберите время для {date_str}:",
            reply_markup=keyboard
        )
        await callback.answer()
    except ValueError as e:
        logger.error(f"Ошибка парсинга даты: {e}, data: {callback.data}")
        await callback.answer("❌ Неверный формат даты", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при выборе даты: {e}, data: {callback.data}")
        await callback.answer("❌ Ошибка при выборе даты", show_alert=True)


@dp.callback_query(F.data.startswith("time_busy_"))
async def callback_time_busy(callback: CallbackQuery):
    """Попытка выбрать занятое или прошедшее время"""
    time_str = callback.data.split("_", 2)[2]
    await callback.answer(f"❌ Время {time_str} занято или недоступно", show_alert=True)


@dp.callback_query(F.data.startswith("time_"))
async def callback_time_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор времени"""
    time_str = callback.data.split("_", 1)[1]
    data = await state.get_data()
    
    service_id = data.get("service_id")
    service_name = data.get("service_name")
    date = data.get("date")
    
    if not all([service_id, date]):
        await callback.answer("❌ Ошибка: не все данные выбраны", show_alert=True)
        return
    
    # Проверяем доступность времени
    times = await db.get_all_times_with_availability(date, service_id)
    time_info = next((t for t in times if t["time"] == time_str), None)
    
    if not time_info or not time_info.get("available", False):
        await callback.answer(f"❌ Время {time_str} недоступно", show_alert=True)
        return
    
    await state.update_data(time=time_str)
    
    # Формируем информацию о записи
    service = await db.get_service(service_id)
    text = f"📋 **Подтверждение записи**\n\n"
    text += f"Услуга: {service_name}\n"
    text += f"Дата: {date}\n"
    text += f"Время: {time_str}\n"
    if service.get("price"):
        text += f"Стоимость: {service['price']:.0f}₽\n"
    text += f"\nПодтвердите запись:"
    
    keyboard = get_confirm_keyboard()
    await state.set_state(BookingStates.waiting_for_confirmation)
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm_None")
async def callback_confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Подтверждение записи"""
    data = await state.get_data()
    
    service_id = data.get("service_id")
    date = data.get("date")
    time = data.get("time")
    
    if not all([service_id, date, time]):
        await callback.answer("❌ Ошибка: не все данные заполнены", show_alert=True)
        return
    
    user = callback.from_user
    
    # Создаём запись
    try:
        appointment_id = await db.add_appointment(
            client_id=user.id,
            client_name=user.full_name or f"{user.first_name} {user.last_name or ''}",
            client_username=user.username,
            service_id=service_id,
            date=date,
            time=time
        )
        
        # Автоматически подтверждаем запись (статус "confirmed")
        await db.confirm_appointment(appointment_id)
        
        service = await db.get_service(service_id)
        text = f"✅ **Запись подтверждена!**\n\n"
        text += f"Номер записи: #{appointment_id}\n"
        text += f"Услуга: {service['name']}\n"
        text += f"Дата: {date}\n"
        text += f"Время: {time}\n"
        if service.get("price"):
            text += f"Стоимость: {service['price']:.0f}₽\n"
        text += f"\nСтатус: ✅ Подтверждена\n\n"
        text += "Мы ждём вас!"
        
        # Добавляем кнопку для просмотра/отмены записи
        keyboard = get_appointment_keyboard(appointment_id, can_cancel=True)
        keyboard.inline_keyboard.insert(0, [
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("✅ Запись создана и подтверждена!")
        
        # Уведомляем администраторов
        await notify_admins_about_new_appointment(appointment_id)
        
        # Автоматический возврат в меню через 5 секунд
        await asyncio.sleep(5)
        try:
            await callback.message.edit_text(
                "🏠 Возврат в главное меню",
                reply_markup=get_main_menu()
            )
        except:
            pass  # Если сообщение уже было изменено, игнорируем ошибку
        
    except Exception as e:
        logger.error(f"Ошибка при создании записи: {e}")
        await callback.answer("❌ Ошибка при создании записи", show_alert=True)
    
    await state.clear()


@dp.callback_query(F.data == "cancel_booking")
async def callback_cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Отмена записи"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Запись отменена.",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "my_appointments")
async def callback_my_appointments(callback: CallbackQuery):
    """Просмотр записей пользователя"""
    user_id = callback.from_user.id
    appointments = await db.get_appointments_by_client(user_id, limit=10)
    
    if not appointments:
        await callback.message.edit_text(
            "📋 У вас пока нет записей.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    
    text = "📋 **Ваши записи:**\n\n"
    for apt in appointments:
        status_emoji = get_status_emoji(apt["status"])
        status_ru = get_status_ru(apt["status"])
        
        text += f"{status_emoji} #{apt['id']} - {apt['service_name']}\n"
        text += f"   📅 {apt['date']} в {apt['time']}\n"
        text += f"   Статус: {status_ru}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("cancel_appointment_"))
async def callback_cancel_appointment(callback: CallbackQuery):
    """Отмена записи пользователем"""
    appointment_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    appointment = await db.get_appointment(appointment_id)
    
    if not appointment or appointment["client_id"] != user_id:
        await callback.answer("❌ Запись не найдена", show_alert=True)
        return
    
    if appointment["status"] == "cancelled":
        await callback.answer("❌ Запись уже отменена", show_alert=True)
        return
    
    success = await db.cancel_appointment(appointment_id)
    
    if success:
        await callback.answer("✅ Запись отменена")
        await callback_main_menu(callback, None)
    else:
        await callback.answer("❌ Ошибка при отмене записи", show_alert=True)


@dp.callback_query(F.data == "view_services")
async def callback_view_services(callback: CallbackQuery):
    """Просмотр услуг"""
    services = await db.get_all_services(active_only=True)
    
    if not services:
        await callback.message.edit_text(
            "❌ Нет доступных услуг.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    
    text = "📋 **Доступные услуги:**\n\n"
    for service in services:
        text += f"• **{service['name']}**\n"
        text += f"  Длительность: {service['duration']} мин.\n"
        if service.get('price'):
            text += f"  Стоимость: {service['price']:.0f}₽\n"
        if service.get('description'):
            text += f"  {service['description']}\n"
        text += "\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Помощь"""
    text = """
📖 **Помощь по использованию бота**

**Как записаться:**
1. Нажмите "📅 Записаться"
2. Выберите услугу
3. Выберите дату
4. Выберите время
5. Подтвердите запись

**Быстрая запись:**
Вы можете написать боту сообщение вида:
• "завтра 15:00"
• "послезавтра в 10"
• "25.12 в 14:30"

**Просмотр записей:**
Нажмите "📋 Мои записи" чтобы увидеть все ваши записи.
"""
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()


# ========== Парсинг естественного языка в сообщениях ==========

@dp.message(BookingStates.waiting_for_date)
async def process_natural_date(message: Message, state: FSMContext):
    """Обработка даты из естественного языка"""
    date_str = parse_natural_date(message.text)
    
    if not date_str:
        await message.answer("❌ Не удалось распознать дату. Попробуйте ещё раз или используйте календарь.")
        return
    
    # Проверяем, что дата не в прошлом
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if selected_date < datetime.now().date():
        await message.answer("❌ Нельзя выбрать прошедшую дату.")
        return
    
    data = await state.get_data()
    service_id = data.get("service_id")
    
    if not service_id:
        await message.answer("❌ Ошибка: услуга не выбрана")
        return
    
    await state.update_data(date=date_str)
    
    # Получаем доступные времена
    times = await db.get_all_times_with_availability(date_str, service_id)
    
    if not times:
        await message.answer("❌ Нет доступных времен на эту дату.")
        return
    
    # Проверяем, есть ли хотя бы одно доступное время
    available_count = sum(1 for t in times if t.get("available", False))
    if available_count == 0:
        await message.answer("❌ Нет свободного времени на эту дату.")
        return
    
    keyboard = get_times_keyboard(times)
    await state.set_state(BookingStates.waiting_for_time)
    await message.answer(
        f"⏰ Выберите время для {date_str}:",
        reply_markup=keyboard
    )


@dp.message(BookingStates.waiting_for_time)
async def process_natural_time(message: Message, state: FSMContext):
    """Обработка времени из естественного языка"""
    time_str = parse_natural_time(message.text)
    
    if not time_str:
        await message.answer("❌ Не удалось распознать время. Попробуйте формат HH:MM (например, 15:00)")
        return
    
    data = await state.get_data()
    service_id = data.get("service_id")
    date = data.get("date")
    
    if not all([service_id, date]):
        await message.answer("❌ Ошибка: не все данные выбраны")
        return
    
    # Проверяем, доступно ли это время
    # Проверяем доступность времени
    times = await db.get_all_times_with_availability(date, service_id)
    time_info = next((t for t in times if t["time"] == time_str), None)
    
    if not time_info or not time_info.get("available", False):
        await message.answer(f"❌ Время {time_str} недоступно. Выберите из предложенных вариантов.")
        return
    
    await state.update_data(time=time_str)
    
    # Формируем информацию о записи
    service = await db.get_service(service_id)
    service_name = data.get("service_name", service["name"])
    
    text = f"📋 **Подтверждение записи**\n\n"
    text += f"Услуга: {service_name}\n"
    text += f"Дата: {date}\n"
    text += f"Время: {time_str}\n"
    if service.get("price"):
        text += f"Стоимость: {service['price']:.0f}₽\n"
    text += f"\nПодтвердите запись:"
    
    keyboard = get_confirm_keyboard()
    await state.set_state(BookingStates.waiting_for_confirmation)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


# ========== Админ-панель ==========

@dp.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery):
    """Админ-панель"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔧 **Админ-панель**\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_settings")
async def callback_admin_settings(callback: CallbackQuery):
    """Настройки администратора"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    # Получаем текущие настройки
    start_hour, end_hour = await db.get_working_hours()
    interval = int(await db.get_setting("appointment_interval", str(config.APPOINTMENT_INTERVAL)))
    
    text = "⚙️ **Настройки бота**\n\n"
    text += f"🕐 Время работы: {start_hour:02d}:00 - {end_hour:02d}:00\n"
    text += f"⏱ Интервал между записями: {interval} мин.\n\n"
    text += "Выберите, что хотите изменить:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🕐 Время начала работы", callback_data="admin_set_work_start"),
            InlineKeyboardButton(text="🕐 Время окончания работы", callback_data="admin_set_work_end")
        ],
        [
            InlineKeyboardButton(text="⏱ Интервал между записями", callback_data="admin_set_interval")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "admin_today")
async def callback_admin_today(callback: CallbackQuery):
    """Записи на сегодня"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    appointments = await db.get_appointments_by_date(today)
    
    if not appointments:
        text = f"📅 На сегодня ({today}) нет записей."
    else:
        text = f"📅 **Записи на сегодня ({today}):**\n\n"
        for apt in appointments:
            status_emoji = get_status_emoji(apt["status"])
            status_ru = get_status_ru(apt["status"])
            
            text += f"{status_emoji} #{apt['id']} - {apt['service_name']}\n"
            text += f"   👤 {apt['client_name']}"
            if apt.get('client_username'):
                text += f" (@{apt['client_username']})"
            text += f"\n   ⏰ {apt['time']}\n"
            text += f"   Статус: {status_ru}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_confirm_appt_"))
async def callback_admin_confirm_appointment(callback: CallbackQuery):
    """Подтверждение записи администратором"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    appointment_id = int(callback.data.split("_")[3])
    appointment = await db.get_appointment(appointment_id)
    
    if not appointment:
        await callback.answer("❌ Запись не найдена", show_alert=True)
        return
    
    success = await db.confirm_appointment(appointment_id)
    
    if success:
        await callback.answer("✅ Запись подтверждена!")
        # Обновляем просмотр записей на эту дату
        date_str = appointment['date']
        # Создаём новый callback для обновления
        class TempCallback:
            def __init__(self, original_callback, new_data):
                self.from_user = original_callback.from_user
                self.message = original_callback.message
                self.data = new_data
                self.answer = original_callback.answer
        
        temp_callback = TempCallback(callback, f"admin_date_{date_str}")
        await callback_admin_view_date(temp_callback)
    else:
        await callback.answer("❌ Ошибка при подтверждении записи", show_alert=True)


@dp.callback_query(F.data.startswith("admin_cancel_appt_"))
async def callback_admin_cancel_appointment(callback: CallbackQuery):
    """Отмена записи администратором"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    appointment_id = int(callback.data.split("_")[3])
    appointment = await db.get_appointment(appointment_id)
    
    if not appointment:
        await callback.answer("❌ Запись не найдена", show_alert=True)
        return
    
    success = await db.cancel_appointment(appointment_id)
    
    if success:
        await callback.answer("✅ Запись отменена!")
        # Обновляем просмотр записей на эту дату
        date_str = appointment['date']
        # Создаём новый callback для обновления
        class TempCallback:
            def __init__(self, original_callback, new_data):
                self.from_user = original_callback.from_user
                self.message = original_callback.message
                self.data = new_data
                self.answer = original_callback.answer
        
        temp_callback = TempCallback(callback, f"admin_date_{date_str}")
        await callback_admin_view_date(temp_callback)
    else:
        await callback.answer("❌ Ошибка при отмене записи", show_alert=True)


@dp.callback_query(F.data.startswith("admin_confirm_appt_"))
async def callback_admin_confirm_appointment(callback: CallbackQuery):
    """Подтверждение записи администратором"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    appointment_id = int(callback.data.split("_")[3])
    success = await db.confirm_appointment(appointment_id)
    
    if success:
        appointment = await db.get_appointment(appointment_id)
        await callback.answer("✅ Запись подтверждена!")
        
        # Обновляем просмотр записей на эту дату
        await callback_admin_view_date(callback)
    else:
        await callback.answer("❌ Ошибка при подтверждении записи", show_alert=True)


@dp.callback_query(F.data.startswith("admin_cancel_appt_"))
async def callback_admin_cancel_appointment(callback: CallbackQuery):
    """Отмена записи администратором"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    appointment_id = int(callback.data.split("_")[3])
    success = await db.cancel_appointment(appointment_id)
    
    if success:
        await callback.answer("✅ Запись отменена!")
        
        # Обновляем просмотр записей на эту дату
        await callback_admin_view_date(callback)
    else:
        await callback.answer("❌ Ошибка при отмене записи", show_alert=True)


@dp.callback_query(F.data == "admin_add_service")
async def callback_admin_add_service(callback: CallbackQuery, state: FSMContext):
    """Начало добавления услуги"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.adding_service_name)
    await callback.message.edit_text(
        "➕ **Добавление новой услуги**\n\n"
        "Введите название услуги:",
        reply_markup=get_back_keyboard("admin_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(AdminStates.adding_service_name)
async def process_service_name(message: Message, state: FSMContext):
    """Обработка названия услуги"""
    service_name = message.text.strip()
    
    if not service_name or len(service_name) < 2:
        await message.answer("❌ Название услуги должно содержать минимум 2 символа. Попробуйте ещё раз:")
        return
    
    await state.update_data(service_name=service_name)
    await state.set_state(AdminStates.adding_service_duration)
    await message.answer(
        f"✅ Название: **{service_name}**\n\n"
        "Введите длительность услуги в минутах (например: 30, 60, 90):",
        reply_markup=get_back_keyboard("admin_panel"),
        parse_mode="Markdown"
    )


@dp.message(AdminStates.adding_service_duration)
async def process_service_duration(message: Message, state: FSMContext):
    """Обработка длительности услуги"""
    try:
        duration = int(message.text.strip())
        if duration <= 0 or duration > 480:  # максимум 8 часов
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное число минут (от 1 до 480). Попробуйте ещё раз:")
        return
    
    await state.update_data(duration=duration)
    await state.set_state(AdminStates.adding_service_price)
    await message.answer(
        f"✅ Длительность: **{duration} минут**\n\n"
        "Введите стоимость услуги в рублях (или 0, если услуга бесплатная):",
        reply_markup=get_back_keyboard("admin_panel"),
        parse_mode="Markdown"
    )


@dp.message(AdminStates.adding_service_price)
async def process_service_price(message: Message, state: FSMContext):
    """Обработка стоимости услуги"""
    try:
        price = float(message.text.strip().replace(',', '.'))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную стоимость (число, например: 1000 или 0). Попробуйте ещё раз:")
        return
    
    await state.update_data(price=price if price > 0 else None)
    await state.set_state(AdminStates.adding_service_description)
    await message.answer(
        f"✅ Стоимость: **{price:.0f}₽**\n\n"
        "Введите описание услуги (или отправьте /skip, чтобы пропустить):",
        reply_markup=get_back_keyboard("admin_panel"),
        parse_mode="Markdown"
    )


@dp.message(Command("skip"), AdminStates.adding_service_description)
@dp.message(AdminStates.adding_service_description)
async def process_service_description(message: Message, state: FSMContext):
    """Обработка описания услуги и сохранение"""
    # Если команда /skip, пропускаем описание
    if message.text and message.text.strip() == "/skip":
        description = None
    else:
        description = message.text.strip() if message.text else None
    
    data = await state.get_data()
    service_name = data.get("service_name")
    duration = data.get("duration")
    price = data.get("price")
    
    if not all([service_name, duration is not None]):
        await message.answer("❌ Ошибка: не все данные заполнены. Начните заново.")
        await state.clear()
        return
    
    try:
        service_id = await db.add_service(
            name=service_name,
            duration=duration,
            price=price,
            description=description
        )
        
        text = f"✅ **Услуга успешно добавлена!**\n\n"
        text += f"ID: #{service_id}\n"
        text += f"Название: {service_name}\n"
        text += f"Длительность: {duration} мин.\n"
        if price:
            text += f"Стоимость: {price:.0f}₽\n"
        if description:
            text += f"Описание: {description}\n"
        
        await message.answer(
            text,
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении услуги: {e}")
        await message.answer(
            "❌ Ошибка при добавлении услуги. Попробуйте ещё раз.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()


@dp.callback_query(F.data == "admin_services")
async def callback_admin_services(callback: CallbackQuery):
    """Список услуг для администратора"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    services = await db.get_all_services(active_only=False)
    
    if not services:
        text = "📋 Услуг пока нет."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ])
    else:
        text = "📋 **Список услуг:**\n\n"
        buttons = []
        active_count = 0
        inactive_count = 0
        
        for service in services:
            is_active = service.get("is_active", True)
            if is_active:
                active_count += 1
            else:
                inactive_count += 1
                # Пропускаем неактивные услуги в списке
                continue
            
            status = "✅" if is_active else "❌"
            text += f"{status} #{service['id']} - **{service['name']}**\n"
            text += f"   Длительность: {service['duration']} мин.\n"
            if service.get('price'):
                text += f"   Стоимость: {service['price']:.0f}₽\n"
            text += "\n"
            
            # Кнопки для каждой услуги
            buttons.append([
                InlineKeyboardButton(
                    text=f"✏️ Редактировать #{service['id']}",
                    callback_data=f"admin_edit_service_{service['id']}"
                ),
                InlineKeyboardButton(
                    text=f"🗑️ Удалить #{service['id']}",
                    callback_data=f"admin_delete_service_{service['id']}"
                )
            ])
        
        if inactive_count > 0:
            text += f"\n_Неактивных услуг: {inactive_count} (скрыты)_"
        
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика для администратора"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    # Получаем статистику из БД
    async with db.get_connection() as conn:
        # Общее количество записей
        cursor = await conn.execute("SELECT COUNT(*) FROM appointments")
        total_appointments = (await cursor.fetchone())[0]
        await cursor.close()
        
        # Записи по статусам
        cursor = await conn.execute("""
            SELECT status, COUNT(*) 
            FROM appointments 
            GROUP BY status
        """)
        rows = await cursor.fetchall()
        status_counts = {row[0]: row[1] for row in rows}
        await cursor.close()
        
        # Количество услуг
        cursor = await conn.execute("SELECT COUNT(*) FROM services WHERE is_active = 1")
        active_services = (await cursor.fetchone())[0]
        await cursor.close()
    
    text = "📊 **Статистика**\n\n"
    text += f"Всего записей: {total_appointments}\n"
    text += f"⏳ Ожидают: {status_counts.get('pending', 0)}\n"
    text += f"✅ Подтверждены: {status_counts.get('confirmed', 0)}\n"
    text += f"❌ Отменены: {status_counts.get('cancelled', 0)}\n\n"
    text += f"Активных услуг: {active_services}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "admin_list")
async def callback_admin_list(callback: CallbackQuery):
    """Список администраторов"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    admins = await db.get_all_admins()
    
    # Добавляем главного администратора из config
    if config.ADMIN_ID not in [a["user_id"] for a in admins]:
        admins.insert(0, {
            "user_id": config.ADMIN_ID,
            "username": None,
            "full_name": "Главный администратор"
        })
    
    text = "👥 **Администраторы:**\n\n"
    for admin in admins:
        text += f"• ID: {admin['user_id']}\n"
        if admin.get('username'):
            text += f"  @{admin['username']}\n"
        if admin.get('full_name'):
            text += f"  {admin['full_name']}\n"
        text += "\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_edit_service_"))
async def callback_admin_edit_service(callback: CallbackQuery, state: FSMContext):
    """Редактирование услуги"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[3])
    service = await db.get_service(service_id)
    
    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    text = f"✏️ **Редактирование услуги #{service_id}**\n\n"
    text += f"Название: {service['name']}\n"
    text += f"Длительность: {service['duration']} мин.\n"
    text += f"Стоимость: {service.get('price', 0) or 0:.0f}₽\n"
    text += f"Описание: {service.get('description', 'Нет')}\n"
    text += f"Статус: {'Активна' if service['is_active'] else 'Неактивна'}\n\n"
    text += "Выберите, что хотите изменить:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название", callback_data=f"admin_edit_field_{service_id}_name")],
        [InlineKeyboardButton(text="⏱ Длительность", callback_data=f"admin_edit_field_{service_id}_duration")],
        [InlineKeyboardButton(text="💰 Стоимость", callback_data=f"admin_edit_field_{service_id}_price")],
        [InlineKeyboardButton(text="📄 Описание", callback_data=f"admin_edit_field_{service_id}_description")],
        [InlineKeyboardButton(text="🔄 Статус (активна/неактивна)", callback_data=f"admin_toggle_service_{service_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_services")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_edit_field_"))
async def callback_admin_edit_field(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования поля услуги"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    parts = callback.data.split("_")
    service_id = int(parts[3])
    field = parts[4]
    
    field_names = {
        "name": "название",
        "duration": "длительность (в минутах)",
        "price": "стоимость (в рублях, или 0)",
        "description": "описание (или /skip для удаления)"
    }
    
    await state.update_data(editing_service_id=service_id, editing_field=field)
    await state.set_state(AdminStates.editing_service_value)
    
    await callback.message.edit_text(
        f"✏️ Введите новое значение для **{field_names.get(field, field)}**:",
        reply_markup=get_back_keyboard("admin_services"),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(AdminStates.editing_service_value)
async def process_edit_service_value(message: Message, state: FSMContext):
    """Обработка нового значения для редактирования услуги"""
    data = await state.get_data()
    service_id = data.get("editing_service_id")
    field = data.get("editing_field")
    
    if not service_id or not field:
        await message.answer("❌ Ошибка: данные не найдены. Начните заново.")
        await state.clear()
        return
    
    try:
        if field == "name":
            new_value = message.text.strip()
            if len(new_value) < 2:
                await message.answer("❌ Название должно содержать минимум 2 символа.")
                return
            await db.update_service(service_id, name=new_value)
            
        elif field == "duration":
            new_value = int(message.text.strip())
            if new_value <= 0 or new_value > 480:
                await message.answer("❌ Длительность должна быть от 1 до 480 минут.")
                return
            await db.update_service(service_id, duration=new_value)
            
        elif field == "price":
            new_value = float(message.text.strip().replace(',', '.'))
            if new_value < 0:
                raise ValueError
            await db.update_service(service_id, price=new_value if new_value > 0 else None)
            
        elif field == "description":
            new_value = message.text.strip() if message.text.strip() != "/skip" else None
            await db.update_service(service_id, description=new_value)
        else:
            await message.answer("❌ Неизвестное поле.")
            await state.clear()
            return
        
        await message.answer(
            f"✅ Поле **{field}** успешно обновлено!",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат данных. Попробуйте ещё раз.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении услуги: {e}")
        await message.answer("❌ Ошибка при обновлении услуги.")
        await state.clear()


@dp.callback_query(F.data.startswith("admin_toggle_service_"))
async def callback_admin_toggle_service(callback: CallbackQuery):
    """Переключение статуса услуги (активна/неактивна)"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[3])
    service = await db.get_service(service_id)
    
    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    # Переключаем статус
    new_status = not service["is_active"]
    await db.update_service(service_id, is_active=1 if new_status else 0)
    
    status_text = "активирована" if new_status else "деактивирована"
    await callback.answer(f"✅ Услуга {status_text}!")
    
    # Возвращаемся к редактированию услуги
    await callback_admin_edit_service(callback, None)


@dp.callback_query(F.data.startswith("admin_delete_service_"))
async def callback_admin_delete_service(callback: CallbackQuery):
    """Удаление услуги"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[3])
    service = await db.get_service(service_id)
    
    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    # Мягкое удаление (деактивация)
    success = await db.delete_service(service_id)
    
    if success:
        await callback.answer("✅ Услуга удалена (деактивирована)!")
        # Обновляем список услуг
        await callback_admin_services(callback)
    else:
        await callback.answer("❌ Ошибка при удалении услуги", show_alert=True)


@dp.callback_query(F.data == "admin_set_work_start")
async def callback_admin_set_work_start(callback: CallbackQuery, state: FSMContext):
    """Настройка времени начала работы"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.setting_working_hours_start)
    await callback.message.edit_text(
        "🕐 **Настройка времени начала работы**\n\n"
        "Введите час начала работы (0-23):\n"
        "Например: 9",
        reply_markup=get_back_keyboard("admin_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_set_work_end")
async def callback_admin_set_work_end(callback: CallbackQuery, state: FSMContext):
    """Настройка времени окончания работы"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.setting_working_hours_end)
    await callback.message.edit_text(
        "🕐 **Настройка времени окончания работы**\n\n"
        "Введите час окончания работы (0-23):\n"
        "Например: 18",
        reply_markup=get_back_keyboard("admin_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(AdminStates.setting_working_hours_start)
async def process_working_hours_start(message: Message, state: FSMContext):
    """Обработка времени начала работы"""
    try:
        hour = int(message.text.strip())
        if hour < 0 or hour > 23:
            await message.answer("❌ Час должен быть от 0 до 23. Попробуйте ещё раз:")
            return
        
        await db.set_setting("working_hours_start", str(hour))
        await message.answer(
            f"✅ Время начала работы установлено: {hour:02d}:00",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректное число (0-23). Попробуйте ещё раз:")


@dp.message(AdminStates.setting_working_hours_end)
async def process_working_hours_end(message: Message, state: FSMContext):
    """Обработка времени окончания работы"""
    try:
        hour = int(message.text.strip())
        if hour < 0 or hour > 23:
            await message.answer("❌ Час должен быть от 0 до 23. Попробуйте ещё раз:")
            return
        
        # Проверяем, что время окончания больше времени начала
        start_hour, _ = await db.get_working_hours()
        if hour <= start_hour:
            await message.answer(f"❌ Время окончания должно быть больше времени начала ({start_hour:02d}:00). Попробуйте ещё раз:")
            return
        
        await db.set_setting("working_hours_end", str(hour))
        await message.answer(
            f"✅ Время окончания работы установлено: {hour:02d}:00",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректное число (0-23). Попробуйте ещё раз:")


@dp.callback_query(F.data == "admin_set_interval")
async def callback_admin_set_interval(callback: CallbackQuery, state: FSMContext):
    """Настройка интервала между записями"""
    user_id = callback.from_user.id
    is_admin = await db.is_admin(user_id) or user_id == config.ADMIN_ID
    
    if not is_admin:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminStates.setting_appointment_interval)
    await callback.message.edit_text(
        "⏱ **Настройка интервала между записями**\n\n"
        "Введите интервал в минутах (например: 30, 60):\n"
        "Минимальный интервал: 15 минут",
        reply_markup=get_back_keyboard("admin_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(AdminStates.setting_appointment_interval)
async def process_appointment_interval(message: Message, state: FSMContext):
    """Обработка интервала между записями"""
    try:
        interval = int(message.text.strip())
        if interval < 15:
            await message.answer("❌ Минимальный интервал - 15 минут. Попробуйте ещё раз:")
            return
        
        if interval > 480:  # Максимум 8 часов
            await message.answer("❌ Максимальный интервал - 480 минут (8 часов). Попробуйте ещё раз:")
            return
        
        await db.set_setting("appointment_interval", str(interval))
        await message.answer(
            f"✅ Интервал между записями установлен: {interval} мин.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректное число (15-480). Попробуйте ещё раз:")


async def notify_admins_about_new_appointment(appointment_id: int):
    """Уведомление администраторов о новой записи"""
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        return
    
    admins = await db.get_all_admins()
    if config.ADMIN_ID not in [a["user_id"] for a in admins]:
        admins.append({"user_id": config.ADMIN_ID})
    
    text = f"🔔 **Новая запись**\n\n"
    text += f"Номер: #{appointment_id}\n"
    text += f"Клиент: {appointment['client_name']}\n"
    if appointment.get('client_username'):
        text += f"Username: @{appointment['client_username']}\n"
    text += f"Услуга: {appointment['service_name']}\n"
    text += f"Дата: {appointment['date']}\n"
    text += f"Время: {appointment['time']}\n"
    text += f"Статус: {get_status_ru(appointment['status'])}"
    
    # Сохраняем сообщения для последующего удаления
    sent_messages = []
    
    for admin in admins:
        try:
            msg = await bot.send_message(admin["user_id"], text, parse_mode="Markdown")
            sent_messages.append(msg)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin['user_id']}: {e}")
    
    # Удаляем сообщения через 5 секунд
    async def delete_messages_after_delay():
        await asyncio.sleep(5)
        for msg in sent_messages:
            try:
                await msg.delete()
            except Exception as e:
                logger.error(f"Не удалось удалить уведомление: {e}")
    
    # Запускаем удаление в фоне
    asyncio.create_task(delete_messages_after_delay())


async def send_appointment_reminder(appointment: dict):
    """Отправить напоминание клиенту о предстоящей записи"""
    try:
        text = "🔔 **Напоминание о записи**\n\n"
        text += f"Через 30 минут у вас запись:\n\n"
        text += f"📋 Услуга: {appointment['service_name']}\n"
        text += f"📅 Дата: {appointment['date']}\n"
        text += f"⏰ Время: {appointment['time']}\n\n"
        text += "Не забудьте прийти вовремя! 😊"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await bot.send_message(
            appointment['client_id'],
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Отмечаем, что напоминание отправлено
        await db.mark_reminder_sent(appointment['id'])
        logger.info(f"Напоминание отправлено клиенту {appointment['client_id']} для записи #{appointment['id']}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания клиенту {appointment.get('client_id')}: {e}")
        return False


async def check_and_send_reminders():
    """Проверка и отправка напоминаний о предстоящих записях"""
    while True:
        try:
            # Получаем записи, которым нужно отправить напоминание
            appointments = await db.get_appointments_for_reminder(minutes_before=30)
            
            for appointment in appointments:
                await send_appointment_reminder(appointment)
                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)
            
            # Проверяем каждую минуту
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в задаче проверки напоминаний: {e}")
            await asyncio.sleep(60)


# ========== Общий обработчик сообщений (в самом конце, после всех состояний) ==========

@dp.message()
async def process_quick_booking(message: Message, state: FSMContext):
    """Обработка быстрой записи через естественный язык"""
    # Проверяем, не находимся ли мы в состоянии добавления услуги или другой операции
    current_state = await state.get_state()
    if current_state:
        # Если мы в каком-то состоянии, пропускаем обработку
        # Пусть специализированные обработчики состояний работают
        return
    
    text = message.text.lower()
    
    # Пытаемся распарсить дату и время из одного сообщения
    date_str = parse_natural_date(message.text)
    time_str = parse_natural_time(message.text)
    
    if date_str and time_str:
        # Быстрая запись
        services = await db.get_all_services(active_only=True)
        
        if not services:
            await message.answer("❌ Нет доступных услуг.")
            return
        
        if len(services) == 1:
            # Если только одна услуга, используем её
            service = services[0]
            service_id = service["id"]
        else:
            # Если несколько услуг, просим выбрать
            await state.set_state(BookingStates.waiting_for_service)
            await state.update_data(quick_date=date_str, quick_time=time_str)
            await message.answer(
                "📋 Выберите услугу:",
                reply_markup=get_services_keyboard(services)
            )
            return
        
        # Проверяем доступность времени
        # Проверяем доступность времени
        times = await db.get_all_times_with_availability(date_str, service_id)
        time_info = next((t for t in times if t["time"] == time_str), None)
        
        if not time_info or not time_info.get("available", False):
            available_times = [t["time"] for t in times if t.get("available", False)]
            await message.answer(
                f"❌ Время {time_str} недоступно на {date_str}.\n"
                f"Доступные времена: {', '.join(available_times[:5])}"
            )
            return
        
        # Создаём запись
        user = message.from_user
        try:
            appointment_id = await db.add_appointment(
                client_id=user.id,
                client_name=user.full_name or f"{user.first_name} {user.last_name or ''}",
                client_username=user.username,
                service_id=service_id,
                date=date_str,
                time=time_str
            )
            
            # Автоматически подтверждаем запись
            await db.confirm_appointment(appointment_id)
            
            text = f"✅ **Запись создана и подтверждена!**\n\n"
            text += f"Номер записи: #{appointment_id}\n"
            text += f"Услуга: {service['name']}\n"
            text += f"Дата: {date_str}\n"
            text += f"Время: {time_str}\n"
            if service.get("price"):
                text += f"Стоимость: {service['price']:.0f}₽\n"
            text += f"\nСтатус: ✅ Подтверждена\n\n"
            text += "Мы ждём вас!"
            
            # Добавляем кнопку для просмотра записи
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            msg = await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
            await notify_admins_about_new_appointment(appointment_id)
            
            # Автоматический возврат в меню через 5 секунд
            await asyncio.sleep(5)
            try:
                await msg.edit_text(
                    "🏠 Возврат в главное меню",
                    reply_markup=get_main_menu()
                )
            except:
                pass  # Если сообщение уже было изменено, игнорируем ошибку
            
        except Exception as e:
            logger.error(f"Ошибка при создании записи: {e}")
            await message.answer("❌ Ошибка при создании записи.")
    else:
        # Не удалось распарсить, показываем главное меню
        await message.answer(
            "Не понял вас. Используйте меню или напишите, например:\n"
            '"завтра 15:00" или "послезавтра в 10"',
            reply_markup=get_main_menu()
        )


# ========== Graceful shutdown ==========

async def on_startup():
    """Инициализация при запуске"""
    logger.info("Запуск бота...")
    await db.init_db()
    logger.info("Бот запущен")
    # Запускаем фоновую задачу для проверки напоминаний
    asyncio.create_task(check_and_send_reminders())
    logger.info("Задача проверки напоминаний запущена")


async def on_shutdown():
    """Очистка при остановке"""
    logger.info("Остановка бота...")
    await bot.session.close()
    logger.info("Бот остановлен")


# ========== Главная функция ==========

async def main():
    """Главная функция"""
    # Регистрация обработчиков startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        # Запуск polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")

