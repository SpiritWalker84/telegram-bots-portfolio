"""
Модуль конфигурации приложения
"""
import os
from typing import Optional
from dataclasses import dataclass

# Загружаем переменные из .env файла
def _load_dotenv():
    """Загружает переменные из .env файла"""
    try:
        from dotenv import load_dotenv
        # Ищем .env файл в корне проекта (на уровень выше config/)
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        env_path = os.path.abspath(env_path)
        
        # Также пробуем найти относительно текущей рабочей директории
        cwd_env = os.path.join(os.getcwd(), '.env')
        
        # Пробуем загрузить из корня проекта
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
        # Если не найден, пробуем в текущей рабочей директории
        elif os.path.exists(cwd_env):
            load_dotenv(cwd_env, override=False)
        else:
            # Если не найден, пробуем в текущей директории (dotenv сам найдет)
            load_dotenv(override=False)
    except ImportError:
        # Если dotenv не установлен, загружаем вручную
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        env_path = os.path.abspath(env_path)
        cwd_env = os.path.join(os.getcwd(), '.env')
        
        # Пробуем загрузить из корня проекта
        if os.path.exists(env_path):
            _load_env_manual(env_path)
        elif os.path.exists(cwd_env):
            _load_env_manual(cwd_env)

def _load_env_manual(env_path):
    """Загружает .env файл вручную"""
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:  # Не перезаписываем существующие
                    os.environ[key] = value

_load_dotenv()


@dataclass
class Config:
    """Класс для хранения конфигурации приложения"""
    
    # API Wildberries (обязательные поля)
    wb_api_key: str
    telegram_bot_token: str
    
    # Опциональные поля со значениями по умолчанию
    wb_api_url: str = "https://marketplace-api.wildberries.ru/api/v3/orders/new"
    wb_poll_interval: int = 180  # 3 минуты в секундах
    telegram_chat_id: Optional[str] = None  # Опционально, будет получен из бота
    db_path: str = "orders.db"
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Создает конфигурацию из переменных окружения
        
        Returns:
            Config: Объект конфигурации
        """
        wb_api_key = os.getenv("WB_API_KEY")
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")  # Опционально
        
        if not wb_api_key:
            raise ValueError("WB_API_KEY не установлен в переменных окружения")
        if not telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
        
        return cls(
            wb_api_key=wb_api_key,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            wb_api_url=os.getenv("WB_API_URL", cls.wb_api_url),
            wb_poll_interval=int(os.getenv("WB_POLL_INTERVAL", cls.wb_poll_interval)),
            db_path=os.getenv("DB_PATH", cls.db_path)
        )
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "Config":
        """
        Создает конфигурацию из словаря
        
        Args:
            config_dict: Словарь с параметрами конфигурации
            
        Returns:
            Config: Объект конфигурации
        """
        return cls(**config_dict)
