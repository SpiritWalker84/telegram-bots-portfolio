"""Конфигурация приложения."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Config(BaseSettings):
    """Класс конфигурации приложения."""
    
    bot_token: str
    admin_chat_id: int
    flask_url: str = "http://localhost:5000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def telegram_api_url(self) -> str:
        """Получить URL Telegram API."""
        return f"https://api.telegram.org/bot{self.bot_token}"
