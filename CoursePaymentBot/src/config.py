"""Configuration management using OOP."""
import logging
import sys
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Bot configuration class loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    # Telegram Bot Configuration
    BOT_TOKEN: str
    
    # Payment Configuration
    PROVIDER_TOKEN: str
    COURSE_PRICE: int = 990
    
    # Channel Configuration
    CHANNEL_ID: str
    
    # Database Configuration
    DB_PATH: str = "bot.db"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "bot.log"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from .env file."""
        try:
            config = cls()
            logger.info("Configuration loaded successfully")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.error("Please check your .env file and ensure all required variables are set")
            sys.exit(1)

    def validate(self) -> bool:
        """Validate configuration values."""
        errors = []
        
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")
        
        if not self.PROVIDER_TOKEN:
            errors.append("PROVIDER_TOKEN is required")
        
        if not self.CHANNEL_ID:
            errors.append("CHANNEL_ID is required")
        
        if self.COURSE_PRICE <= 0:
            errors.append("COURSE_PRICE must be greater than 0")
        
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        return True
