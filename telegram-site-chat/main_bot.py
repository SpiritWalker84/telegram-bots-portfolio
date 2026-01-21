"""Точка входа для Telegram бота."""
import asyncio
import logging
from aiogram import Bot, Dispatcher

from src.config import Config
from src.bot.handlers import BotHandlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция для запуска бота."""
    try:
        # Инициализация конфигурации
        config = Config()
        logger.info("Конфигурация загружена успешно")
        
        # Инициализация бота и диспетчера
        bot = Bot(token=config.bot_token)
        dp = Dispatcher()
        
        # Инициализация обработчиков
        bot_handlers = BotHandlers(dp, config)
        logger.info("Обработчики зарегистрированы")
        
        # Запуск бота
        logger.info("Бот запущен и ожидает сообщения...")
        await dp.start_polling(bot)
    
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
