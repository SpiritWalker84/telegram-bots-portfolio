"""Main bot file."""
import asyncio
import logging
import signal
import sys
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import Config
from src.database.models import Database
from src.services.payment_service import PaymentService
from src.services.user_service import UserService
from src.bot.handlers import router

# Флаг для корректного завершения
_shutdown_flag = False



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main bot function."""
    # Load configuration
    config = Config.load()
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)
    
    # Configure logging with file handler if specified
    if config.LOG_FILE:
        file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Initialize database
    db = Database(config.DB_PATH)
    await db.create_table()

    # Initialize services
    payment_service = PaymentService(
        provider_token=config.PROVIDER_TOKEN,
        course_price=config.COURSE_PRICE
    )
    user_service = UserService(db=db)

    # Register router
    dp.include_router(router)

    # Inject dependencies via middleware
    class DependencyMiddleware(BaseMiddleware):
        async def __call__(
            self,
            handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: Dict[str, Any],
        ) -> Any:
            data["db"] = db
            data["payment_service"] = payment_service
            data["user_service"] = user_service
            data["channel_id"] = config.CHANNEL_ID
            data["course_price"] = config.COURSE_PRICE
            return await handler(event, data)

    dp.message.middleware(DependencyMiddleware())
    dp.callback_query.middleware(DependencyMiddleware())
    dp.pre_checkout_query.middleware(DependencyMiddleware())

    # Graceful shutdown handler
    def signal_handler(sig, frame):
        global _shutdown_flag
        logger.info("Received shutdown signal")
        _shutdown_flag = True
        asyncio.create_task(shutdown(bot, dp))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Bot starting...")
        # Запуск polling - aiogram сам обрабатывает сетевые ошибки
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Error in polling: {e}")
    finally:
        await shutdown(bot, dp)


async def shutdown(bot: Bot, dp: Dispatcher) -> None:
    """Graceful shutdown."""
    global _shutdown_flag
    _shutdown_flag = True
    
    logger.info("Shutting down...")
    
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
    
    logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
