"""
Основной файл Telegram Booking Bot
"""
import asyncio
import logging
import signal
import sys
from typing import Optional

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import Config
from src.database.models import Database
from src.services.reminders import check_and_send_reminders
from src.bot.handlers import router as base_router

logger = logging.getLogger(__name__)


## Helper functions moved to src/utils/helpers.py
## FSM states moved to src/bot/states.py
## Natural language parsing moved to src/utils/nlp.py


# ========== Команды ==========

## Base commands/main_menu/help callback moved to src/bot/handlers.py (Router-based)


# ========== Обработчики callback ==========

## Все обработчики (booking flow + admin panel) перенесены в src/bot/handlers.py (Router-based)


## Notifications and reminders moved to src/services (see src/services/*.py)
## Quick booking handler moved to src/bot/handlers.py


# Флаг для корректного завершения
_shutdown_flag = False


async def start_polling_with_retry(bot: Bot, dp: Dispatcher, max_retries: int = None):
    """
    Запуск polling с автоматическим переподключением при сетевых ошибках.
    
    Args:
        bot: Экземпляр бота
        dp: Экземпляр диспетчера
        max_retries: Максимальное количество попыток (None = бесконечно)
    """
    retry_count = 0
    while not _shutdown_flag:
        try:
            logger.info("Запуск polling...")
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            # Если polling завершился без ошибки, выходим
            break
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            break
        except Exception as e:
            retry_count += 1
            if max_retries and retry_count > max_retries:
                logger.error(f"Достигнуто максимальное количество попыток ({max_retries}). Остановка.")
                raise
            
            logger.warning(
                f"Ошибка при polling (попытка {retry_count}): {e}. "
                f"Переподключение через 10 секунд..."
            )
            await asyncio.sleep(10)




# ========== Главная функция ==========

async def main():
    """Главная функция"""
    global _shutdown_flag
    
    # Загрузка конфигурации
    try:
        config = Config.load()
        if not config.validate():
            logger.error("Configuration validation failed. Please check your .env file.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Настройка логирования
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger.info("Configuration loaded and logging configured")
    
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
    
    # Register router
    dp.include_router(base_router)
    
    # Регистрация обработчиков startup/shutdown
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
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Обработка сигналов для корректного завершения
    def signal_handler(sig, frame):
        global _shutdown_flag
        logger.info("Получен сигнал завершения")
        _shutdown_flag = True
        asyncio.create_task(on_shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запуск polling с retry-логикой
        await start_polling_with_retry(bot, dp)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")

