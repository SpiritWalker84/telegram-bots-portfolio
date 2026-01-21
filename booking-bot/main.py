"""
Основной файл Telegram Booking Bot
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from dateutil import parser as date_parser

from src.config import Config
from src.database.models import Database
from src.bot.keyboards import (
    get_main_menu,
    get_services_keyboard,
    get_calendar_keyboard,
    get_times_keyboard,
    get_confirm_keyboard,
    get_appointment_keyboard,
    get_admin_keyboard,
    get_back_keyboard,
    get_admin_calendar_keyboard,
)
from src.bot.states import BookingStates, AdminStates
from src.utils.nlp import parse_natural_date, parse_natural_time
from src.utils.helpers import get_status_ru, get_status_emoji
from src.services.notifications import notify_admins_about_new_appointment
from src.services.reminders import check_and_send_reminders
from src.bot.handlers import router as base_router

# Загрузка конфигурации
config = Config.load()
if not config.validate():
    raise ValueError("Configuration validation failed. Please check your .env file.")

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


# Dependency injection for Router-based handlers
class DependencyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        data["db"] = db
        data["admin_id"] = config.ADMIN_ID
        data["bot"] = bot
        data["config"] = config  # Pass config for handlers that need it
        return await handler(event, data)


dp.message.middleware(DependencyMiddleware())
dp.callback_query.middleware(DependencyMiddleware())

# Register router (we migrate legacy handlers gradually)
dp.include_router(base_router)


## Helper functions moved to src/utils/helpers.py
## FSM states moved to src/bot/states.py
## Natural language parsing moved to src/utils/nlp.py


# ========== Команды ==========

## Base commands/main_menu/help callback moved to src/bot/handlers.py (Router-based)


# ========== Обработчики callback ==========

## Все обработчики (booking flow + admin panel) перенесены в src/bot/handlers.py (Router-based)


## Notifications and reminders moved to src/services (see src/services/*.py)
## Quick booking handler moved to src/bot/handlers.py


# ========== Graceful shutdown ==========

async def on_startup():
    """Инициализация при запуске"""
    logger.info("Запуск бота...")
    await db.init_db()
    logger.info("Бот запущен")
    # Запускаем фоновую задачу для проверки напоминаний
    asyncio.create_task(check_and_send_reminders(bot=bot, db=db, minutes_before=30))
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

