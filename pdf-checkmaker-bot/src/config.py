"""Configuration management for pdf-checkmaker-bot."""

import logging
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Bot configuration loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    # Telegram Bot
    BOT_TOKEN: str

    # Admin (optional – if not set, bot is open for all users)
    ADMIN_ID: int | None = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "bot.log"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment / .env file."""
        try:
            config = cls()
            logger.info("Configuration loaded successfully")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.error("Please check your .env file and ensure all required variables are set")
            sys.exit(1)

    def validate(self) -> bool:
        """Validate configuration values and log problems."""
        errors: list[str] = []

        if not self.BOT_TOKEN or self.BOT_TOKEN == "your_bot_token_here":
            errors.append("BOT_TOKEN is required and must be set in .env file")

        # ADMIN_ID is optional by design – when missing, bot is available for everyone

        if errors:
            for err in errors:
                logger.error(err)
            return False

        if self.ADMIN_ID is None:
            logger.warning(
                "ADMIN_ID is not set – bot will be available for all users. "
                "Set ADMIN_ID in .env to restrict access."
            )

        logger.info("Configuration validation passed")
        return True

