"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

# ID администратора
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
if ADMIN_ID == 0:
    raise ValueError("ADMIN_ID не найден в .env файле")

# Путь к базе данных
DB_PATH = os.getenv("DB_PATH", "booking_bot.db")

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# Настройки времени работы (часы)
WORKING_HOURS_START = int(os.getenv("WORKING_HOURS_START", "9"))
WORKING_HOURS_END = int(os.getenv("WORKING_HOURS_END", "18"))

# Интервал между записями (минуты)
APPOINTMENT_INTERVAL = int(os.getenv("APPOINTMENT_INTERVAL", "30"))




