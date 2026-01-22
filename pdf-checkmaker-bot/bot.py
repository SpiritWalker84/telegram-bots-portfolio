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
import signal
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import Config
from src.bot.handlers import router

# Флаг для корректного завершения
_shutdown_flag = False




async def shutdown(bot: Bot, dp: Dispatcher):
    """Корректное завершение работы бота."""
    global _shutdown_flag
    _shutdown_flag = True
    
    logger.info("Остановка бота...")
    
    # Остановка polling
    try:
        await dp.stop_polling()
    except Exception as e:
        logger.warning(f"Ошибка при остановке polling: {e}")
    
    # Закрытие сессии бота
    try:
        await bot.session.close()
    except Exception as e:
        logger.warning(f"Ошибка при закрытии сессии бота: {e}")
    
    logger.info("Бот остановлен")

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
    global _shutdown_flag
    
    # Регистрируем роутер
    dp.include_router(router)
    
    # Удаляем webhook если он был установлен (для избежания конфликтов)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удален (если был установлен)")
    except Exception as e:  # noqa: BLE001
        logger.warning("Не удалось удалить webhook: %s", e)
    
    # Обработка сигналов для корректного завершения
    def signal_handler(sig, frame):
        global _shutdown_flag
        logger.info("Получен сигнал завершения")
        _shutdown_flag = True
        asyncio.create_task(shutdown(bot, dp))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Бот запущен!")
    
    try:
        # Запускаем polling - aiogram сам обрабатывает сетевые ошибки
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await shutdown(bot, dp)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:  # noqa: BLE001
        logger.error("Критическая ошибка: %s", e, exc_info=True)

