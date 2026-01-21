"""Главный файл для запуска бота (новая модульная версия)."""
import asyncio

from aiogram import Bot, Dispatcher

from src.config import Config
from src.database.models import Database
from src.services.task_service import TaskService
from src.services.reminder_service import ReminderService
from src.bot.handlers import BotHandlers


async def main():
    """Главная функция запуска бота."""
    try:
        # Загрузка конфигурации
        config = Config()
        print("✅ Конфигурация загружена")
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return
    except Exception as e:
        print(f"❌ Неожиданная ошибка при загрузке конфигурации: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    
    # Инициализация базы данных
    database = Database(config.db_name)
    await database.init_db()
    print("✅ База данных инициализирована")
    
    # Инициализация сервисов
    task_service = TaskService(database)
    reminder_service = ReminderService(bot, database)
    
    # Регистрация обработчиков
    handlers = BotHandlers(task_service, database)
    handlers.register_handlers(dp)
    print("✅ Обработчики зарегистрированы")
    
    # Запуск фонового цикла для напоминаний
    reminder_service.start()
    print("✅ Цикл напоминаний запущен")
    
    try:
        # Проверка подключения
        bot_info = await bot.get_me()
        print(f"✅ Бот подключён: @{bot_info.username} ({bot_info.first_name})")
        
        # Запуск бота
        print("🚀 Бот запущен и ожидает сообщения...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\n⏹️  Остановка бота...")
    finally:
        # Остановка фонового цикла
        await reminder_service.stop()
        
        # Закрытие сессии бота
        await bot.session.close()
        print("✅ Бот остановлен")


if __name__ == "__main__":
    try:
        print("🚀 Запуск бота...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")