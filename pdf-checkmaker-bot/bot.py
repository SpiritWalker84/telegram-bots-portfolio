"""
Entry point for pdf-checkmaker-bot.

Only responsibility here:
- load configuration
- configure logging
- create Bot / Dispatcher
- include router with handlers
- start polling
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import Config
from src.bot.handlers import router

#
# Загрузка и валидация конфигурации
# ------------------------------------------------------------
config = Config.load()
if not config.validate():
    raise ValueError("Configuration validation failed. Please check your .env file.")

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


async def main() -> None:
    """Главная функция запуска бота."""
    # Регистрируем роутер
    dp.include_router(router)
    
    # Удаляем webhook если он был установлен (для избежания конфликтов)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален (если был установлен)")
    except Exception as e:  # noqa: BLE001
        logger.warning("Не удалось удалить webhook: %s", e)
    
    logger.info("Бот запущен!")
    
    # Запускаем polling
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:  # noqa: BLE001
        logger.error("Критическая ошибка: %s", e, exc_info=True)

