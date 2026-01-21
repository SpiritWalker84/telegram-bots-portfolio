"""Маршруты Flask сервера."""
import logging
from flask import Flask, request, jsonify
from typing import Optional

from ..config import Config
from ..services.reply_service import ReplyService
from ..services.message_service import MessageService

logger = logging.getLogger(__name__)


class ServerRoutes:
    """Класс для управления маршрутами Flask сервера."""
    
    def __init__(self, app: Flask, config: Config):
        """
        Инициализация маршрутов.
        
        Args:
            app: Flask приложение
            config: Конфигурация приложения
        """
        self.app = app
        self.config = config
        self.reply_service = ReplyService()
        self.message_service = MessageService(config)
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Зарегистрировать все маршруты."""
        self.app.route('/send_message', methods=['POST'])(self.send_message)
        self.app.route('/admin_reply', methods=['POST'])(self.admin_reply)
        self.app.route('/get_replies', methods=['GET'])(self.get_replies)
    
    def send_message(self) -> tuple:
        """
        Обработчик POST /send_message - отправка сообщения с сайта администратору.
        
        Returns:
            JSON ответ с результатом отправки
        """
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'Missing JSON data'}), 400
            
            site_chat_id = data.get('chat_id')
            message = data.get('message')
            
            if not site_chat_id or not message:
                return jsonify({'error': 'Missing chat_id or message'}), 400
            
            # Отправляем сообщение админу в Telegram
            if self.message_service.send_to_admin(site_chat_id, message):
                # Инициализируем список ответов для этого chat_id, если его нет
                self.reply_service.initialize_chat(site_chat_id)
                logger.info(f"Сообщение отправлено админу: chat_id={site_chat_id}")
                return jsonify({'status': 'sent'})
            else:
                logger.error(f"Не удалось отправить сообщение админу: chat_id={site_chat_id}")
                return jsonify({'error': 'Failed to send'}), 500
        
        except Exception as e:
            logger.error(f"Ошибка в send_message: {e}")
            return jsonify({'error': str(e)}), 500
    
    def admin_reply(self) -> tuple:
        """
        Обработчик POST /admin_reply - получение ответов от бота.
        
        Returns:
            JSON ответ с результатом сохранения
        """
        try:
            data = request.json
            if not data:
                logger.error("Отсутствует JSON data в admin_reply")
                return jsonify({'error': 'Missing JSON data'}), 400
            
            site_chat_id = data.get('site_chat_id')
            message = data.get('message')
            
            if not site_chat_id or not message:
                logger.error(f"Отсутствует site_chat_id или message: {data}")
                return jsonify({'error': 'Missing site_chat_id or message'}), 400
            
            # Сохраняем ответ для отправки на сайт
            self.reply_service.add_reply(site_chat_id, message)
            
            logger.info(f"Ответ сохранен для chat_id={site_chat_id}, message={message}")
            return jsonify({'status': 'received'})
        
        except Exception as e:
            logger.error(f"Ошибка в admin_reply: {e}")
            return jsonify({'error': str(e)}), 500
    
    def get_replies(self) -> tuple:
        """
        Обработчик GET /get_replies - получение ответов администратора для конкретного chat_id.
        
        Returns:
            JSON ответ со списком ответов
        """
        try:
            site_chat_id = request.args.get('chat_id')
            
            if not site_chat_id:
                return jsonify({'error': 'Missing chat_id'}), 400
            
            # Получаем и очищаем ответы для этого chat_id
            replies = self.reply_service.get_and_clear_replies(site_chat_id)
            
            if replies:
                logger.info(f"Отправлено {len(replies)} ответов для chat_id={site_chat_id}")
            else:
                logger.debug(f"Нет ответов для chat_id={site_chat_id}")
            
            return jsonify({'replies': replies})
        
        except Exception as e:
            logger.error(f"Ошибка в get_replies: {e}")
            return jsonify({'error': str(e)}), 500
