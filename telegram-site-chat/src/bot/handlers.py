"""Обработчики команд и сообщений Telegram бота."""
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

from ..config import Config
from ..services.message_service import MessageService
from ..utils.parsers import ChatIdParser

logger = logging.getLogger(__name__)


class BotHandlers:
    """Класс обработчиков для Telegram бота."""
    
    def __init__(self, dp: Dispatcher, config: Config):
        """
        Инициализация обработчиков.
        
        Args:
            dp: Диспетчер aiogram
            config: Конфигурация приложения
        """
        self.dp = dp
        self.config = config
        self.message_service = MessageService(config)
        self.chat_id_parser = ChatIdParser()
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Зарегистрировать все обработчики."""
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.message.register(self.admin_message, F.chat.id == self.config.admin_chat_id)
        self.dp.message.register(self.site_message)  # Обработчик по умолчанию
    
    async def start_handler(self, message: types.Message) -> None:
        """
        Обработчик команды /start.
        
        Args:
            message: Сообщение от пользователя
        """
        await message.answer("Бот для сайта готов! Жду сообщений с сайта.")
        logger.info(f"Пользователь {message.from_user.id} запустил бота")
    
    async def admin_message(self, message: types.Message) -> None:
        """
        Обработчик сообщений от администратора.
        
        Args:
            message: Сообщение от администратора
        """
        if not message.reply_to_message:
            await message.answer("💡 Ответьте на сообщение от сайта (reply), чтобы отправить ответ.")
            return
        
        # Извлекаем site_chat_id из текста сообщения
        site_chat_id = None
        if message.reply_to_message.text:
            site_chat_id = self.chat_id_parser.extract_site_chat_id(message.reply_to_message.text)
            if site_chat_id:
                logger.info(f"Извлечен site_chat_id: {site_chat_id} из текста: {message.reply_to_message.text[:100]}")
            else:
                logger.warning(f"Не удалось извлечь chat_id из: {message.reply_to_message.text[:100]}")
        
        if not site_chat_id:
            await message.answer("❌ Не найден site_chat_id в сообщении. Ответьте на сообщение с сайта (которое содержит chat_id).")
            return
        
        # Отправляем ответ на Flask сервер
        if not message.text:
            await message.answer("⚠️ Сообщение пустое. Пожалуйста, отправьте текст ответа.")
            return
        
        logger.info(f"Отправка ответа на Flask: chat_id={site_chat_id}, message={message.text}")
        
        if self.message_service.send_reply_to_flask(site_chat_id, message.text):
            await message.answer("✅ Ответ отправлен на сайт")
        else:
            await message.answer("⚠️ Не удалось отправить ответ на сайт. Проверьте, что Flask сервер запущен.")
    
    async def site_message(self, message: types.Message) -> None:
        """
        Обработчик прочих сообщений (игнорирует сообщения не от админа).
        
        Args:
            message: Сообщение от пользователя
        """
        # Игнорируем сообщения, которые не от админа (они обрабатываются через Flask)
        pass
