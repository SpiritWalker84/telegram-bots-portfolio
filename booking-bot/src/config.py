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
    
    # Admin Configuration
    ADMIN_ID: int
    
    # Database Configuration
    DB_PATH: str = "booking_bot.db"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "bot.log"
    
    # Working Hours Configuration
    WORKING_HOURS_START: int = 9
    WORKING_HOURS_END: int = 18
    
    # Appointment Configuration
    APPOINTMENT_INTERVAL: int = 30

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
        
        if not self.BOT_TOKEN or self.BOT_TOKEN == "your_bot_token_here":
            errors.append("BOT_TOKEN is required and must be set in .env file")
        
        if not self.ADMIN_ID or self.ADMIN_ID == 0:
            errors.append("ADMIN_ID is required and must be set in .env file")
        
        if self.WORKING_HOURS_START < 0 or self.WORKING_HOURS_START > 23:
            errors.append("WORKING_HOURS_START must be between 0 and 23")
        
        if self.WORKING_HOURS_END < 0 or self.WORKING_HOURS_END > 23:
            errors.append("WORKING_HOURS_END must be between 0 and 23")
        
        if self.WORKING_HOURS_START >= self.WORKING_HOURS_END:
            errors.append("WORKING_HOURS_START must be less than WORKING_HOURS_END")
        
        if self.APPOINTMENT_INTERVAL < 15:
            errors.append("APPOINTMENT_INTERVAL must be at least 15 minutes")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        logger.info("Configuration validation passed")
        return True
