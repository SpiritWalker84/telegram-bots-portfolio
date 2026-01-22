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
from aiogram.exceptions import TelegramBadRequest

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
    
    # Middleware для безопасной обработки callback при остановке
    class SafeCallbackMiddleware(BaseMiddleware):
        async def __call__(self, handler, event, data):
            try:
                return await handler(event, data)
            except TelegramBadRequest as e:
                error_msg = str(e).lower()
                # Игнорируем ошибки "query is too old" при остановке бота
                if "query is too old" in error_msg or "query id is invalid" in error_msg:
                    logger.debug(f"Ignoring old callback query during shutdown: {e}")
                    return
                # Игнорируем ошибку "message is not modified" - это нормально, если сообщение уже имеет нужное содержимое
                if "message is not modified" in error_msg:
                    logger.debug(f"Ignoring 'message is not modified' error: {e}")
                    return
                raise
            except Exception as e:
                # Если бот останавливается, игнорируем ошибки
                if _shutdown_flag:
                    logger.debug(f"Ignoring error during shutdown: {e}")
                    return
                raise
    
    dp.message.middleware(DependencyMiddleware())
    dp.callback_query.middleware(DependencyMiddleware())
    dp.callback_query.middleware(SafeCallbackMiddleware())
    
    # Register router
    dp.include_router(base_router)
    
    # Переменная для хранения фоновой задачи
    reminder_task = None
    
    # Регистрация обработчиков startup/shutdown
    async def on_startup():
        """Инициализация при запуске"""
        nonlocal reminder_task
        logger.info("Запуск бота...")
        await db.init_db()
        logger.info("Бот запущен")
        # Запускаем фоновую задачу для проверки напоминаний и сохраняем ссылку
        reminder_task = asyncio.create_task(check_and_send_reminders(bot=bot, db=db, minutes_before=30))
        logger.info("Задача проверки напоминаний запущена")
    
    async def on_shutdown():
        """Очистка при остановке"""
        nonlocal reminder_task
        global _shutdown_flag
        _shutdown_flag = True
        
        logger.info("Остановка бота...")
        
        # Отменяем фоновую задачу проверки напоминаний
        if reminder_task and not reminder_task.done():
            logger.info("Отмена задачи проверки напоминаний...")
            reminder_task.cancel()
            try:
                await reminder_task
            except asyncio.CancelledError:
                logger.info("Задача проверки напоминаний отменена")
            except Exception as e:
                logger.warning(f"Ошибка при отмене задачи проверки напоминаний: {e}")
        
        # Остановка polling (это остановит обработку новых обновлений)
        try:
            await dp.stop_polling()
            logger.info("Polling остановлен")
        except Exception as e:
            logger.warning(f"Ошибка при остановке polling: {e}")
        
        # Даем время на завершение обработки текущих обновлений
        await asyncio.sleep(1)
        
        # Закрытие сессии бота
        try:
            await bot.session.close()
            logger.info("Сессия бота закрыта")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии сессии бота: {e}")
        
        logger.info("Бот остановлен")
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Обработка сигналов для корректного завершения
    # Aiogram сам обрабатывает SIGINT/SIGTERM через dp.start_polling()
    # Но мы добавляем простой обработчик для установки флага
    def signal_handler(sig, frame):
        global _shutdown_flag
        logger.info(f"Получен сигнал завершения: {sig}")
        _shutdown_flag = True
    
    # Регистрируем обработчики сигналов только для Unix-систем
    if sys.platform != 'win32':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запуск polling - aiogram сам обрабатывает SIGINT/SIGTERM и сетевые ошибки
        logger.info("Запуск polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (KeyboardInterrupt)")
        _shutdown_flag = True
    except asyncio.CancelledError:
        logger.info("Получен сигнал отмены")
        _shutdown_flag = True
    except Exception as e:
        logger.error(f"Критическая ошибка при polling: {e}", exc_info=True)
        _shutdown_flag = True
    finally:
        if not _shutdown_flag:
            _shutdown_flag = True
        await on_shutdown()


if __name__ == "__main__":
    try:
        # Используем asyncio.run() который правильно обрабатывает сигналы
        asyncio.run(main())
    except KeyboardInterrupt:
        # Это должно сработать, если сигнал не был обработан внутри main()
        print("\nПолучен сигнал остановки (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

