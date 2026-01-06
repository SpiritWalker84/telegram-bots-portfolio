"""Main bot file."""
import asyncio
import logging
import signal
import sys
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from pydantic_settings import BaseSettings, SettingsConfigDict

from database import Database
from handlers import router


class Settings(BaseSettings):
    """Bot settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    BOT_TOKEN: str
    PROVIDER_TOKEN: str
    COURSE_PRICE: int = 990
    CHANNEL_ID: str
    DB_PATH: str = "bot.db"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main bot function."""
    # Load settings
    try:
        settings = Settings()
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        sys.exit(1)

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Initialize database
    db = Database(settings.DB_PATH)
    await db.create_table()

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
            data["provider_token"] = settings.PROVIDER_TOKEN
            data["course_price"] = settings.COURSE_PRICE
            data["channel_id"] = settings.CHANNEL_ID
            return await handler(event, data)

    dp.message.middleware(DependencyMiddleware())
    dp.callback_query.middleware(DependencyMiddleware())
    dp.pre_checkout_query.middleware(DependencyMiddleware())

    # Graceful shutdown handler
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(shutdown(bot, dp))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Bot starting...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in polling: {e}")
    finally:
        await shutdown(bot, dp)


async def shutdown(bot: Bot, dp: Dispatcher) -> None:
    """Graceful shutdown."""
    logger.info("Shutting down...")
    await bot.session.close()
    await dp.stop_polling()
    logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

