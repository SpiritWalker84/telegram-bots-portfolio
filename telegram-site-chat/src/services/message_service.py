"""Сервис для отправки сообщений в Telegram."""
import requests
import logging
from typing import Optional
from ..config import Config

logger = logging.getLogger(__name__)


class MessageService:
    """Класс для отправки сообщений в Telegram."""
    
    def __init__(self, config: Config):
        """
        Инициализация сервиса.
        
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.telegram_api_url = config.telegram_api_url
    
    def send_to_admin(self, site_chat_id: str, message: str) -> bool:
        """
        Отправить сообщение администратору в Telegram.
        
        Args:
            site_chat_id: ID чата на сайте
            message: Текст сообщения
            
        Returns:
            True, если сообщение отправлено успешно, иначе False
        """
        url = f"{self.telegram_api_url}/sendMessage"
        payload = {
            'chat_id': self.config.admin_chat_id,
            'text': f"Сообщение с сайта (chat_id: {site_chat_id}):\n{message}"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Сообщение отправлено админу: chat_id={site_chat_id}")
                return True
            else:
                logger.error(f"Ошибка отправки сообщения: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"Исключение при отправке сообщения: {e}")
            return False
    
    def send_reply_to_flask(self, site_chat_id: str, message: str) -> bool:
        """
        Отправить ответ администратора на Flask сервер.
        
        Args:
            site_chat_id: ID чата на сайте
            message: Текст ответа
            
        Returns:
            True, если ответ отправлен успешно, иначе False
        """
        url = f"{self.config.flask_url}/admin_reply"
        payload = {
            'site_chat_id': site_chat_id,
            'message': message
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info(f"Ответ отправлен на Flask: chat_id={site_chat_id}")
                return True
            else:
                logger.error(f"Ошибка отправки ответа на Flask: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"Исключение при отправке ответа на Flask: {e}")
            return False
