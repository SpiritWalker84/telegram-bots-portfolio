"""Главный файл для запуска бота (новая модульная версия)."""
import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher

from src.config import Config
from src.database.models import Database
from src.services.task_service import TaskService
from src.services.reminder_service import ReminderService
from src.bot.handlers import BotHandlers

logger = logging.getLogger(__name__)

# Флаг для корректного завершения
_shutdown_flag = False




async def main():
    """Главная функция запуска бота."""
    global _shutdown_flag
    
    try:
        # Загрузка конфигурации
        config = Config()
        logger.info("✅ Конфигурация загружена")
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при загрузке конфигурации: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    
    # Инициализация базы данных
    database = Database(config.db_name)
    await database.init_db()
    logger.info("✅ База данных инициализирована")
    
    # Инициализация сервисов
    task_service = TaskService(database)
    reminder_service = ReminderService(bot, database)
    
    # Регистрация обработчиков
    handlers = BotHandlers(task_service, database)
    handlers.register_handlers(dp)
    logger.info("✅ Обработчики зарегистрированы")
    
    # Запуск фонового цикла для напоминаний
    reminder_service.start()
    logger.info("✅ Цикл напоминаний запущен")
    
    # Обработка сигналов для корректного завершения
    def signal_handler(sig, frame):
        global _shutdown_flag
        logger.info("Получен сигнал завершения")
        _shutdown_flag = True
        asyncio.create_task(shutdown(bot, dp, reminder_service))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Проверка подключения
        bot_info = await bot.get_me()
        logger.info(f"✅ Бот подключён: @{bot_info.username} ({bot_info.first_name})")
        
        # Запуск бота - aiogram сам обрабатывает сетевые ошибки
        logger.info("🚀 Бот запущен и ожидает сообщения...")
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("\n⏹️  Остановка бота...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в main(): {e}", exc_info=True)
        # Не выходим сразу, даем возможность корректно завершиться
    finally:
        await shutdown(bot, dp, reminder_service)


async def shutdown(bot: Bot, dp: Dispatcher, reminder_service: ReminderService):
    """Корректное завершение работы бота."""
    global _shutdown_flag
    _shutdown_flag = True
    
    logger.info("Остановка бота...")
    
    # Остановка polling
    try:
        await dp.stop_polling()
    except Exception as e:
        logger.warning(f"Ошибка при остановке polling: {e}")
    
    # Остановка фонового цикла
    try:
        await reminder_service.stop()
    except Exception as e:
        logger.warning(f"Ошибка при остановке reminder_service: {e}")
    
    # Закрытие сессии бота
    try:
        await bot.session.close()
    except Exception as e:
        logger.warning(f"Ошибка при закрытии сессии бота: {e}")
    
    logger.info("✅ Бот остановлен")


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    try:
        logger.info("🚀 Запуск бота...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 До свидания!")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")
