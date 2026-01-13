"""
Модуль для работы с Telegram ботом
"""
import logging
import time
from typing import Optional
import requests


class TelegramBot:
    """Класс для отправки уведомлений в Telegram"""
    
    def __init__(self, bot_token: str, chat_id: Optional[str] = None):
        """
        Инициализация Telegram бота
        
        Args:
            bot_token: Токен бота
            chat_id: ID чата для отправки сообщений (опционально, будет получен из обновлений)
        """
        self.bot_token = bot_token
        self._chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = logging.getLogger(__name__)
        self.last_update_id = 0
    
    @property
    def chat_id(self) -> Optional[str]:
        """Получает chat_id"""
        return self._chat_id
    
    @chat_id.setter
    def chat_id(self, value: str) -> None:
        """Устанавливает chat_id"""
        self._chat_id = value
        self.logger.info(f"Chat ID установлен: {value}")
    
    def send_message(self, text: str, parse_mode: Optional[str] = "HTML", chat_id: Optional[str] = None) -> bool:
        """
        Отправляет сообщение в Telegram
        
        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML или Markdown)
            chat_id: ID чата (если не указан, используется сохраненный)
            
        Returns:
            bool: True если сообщение отправлено успешно, False иначе
        """
        target_chat_id = chat_id or self.chat_id
        
        if not target_chat_id:
            self.logger.error("Chat ID не установлен. Отправьте команду /start боту.")
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.debug("Сообщение успешно отправлено в Telegram")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
            return False
    
    def format_order_notification(self, order) -> str:
        """
        Форматирует уведомление о новом заказе
        
        Args:
            order: Объект Order
            
        Returns:
            str: Отформатированное сообщение
        """
        if order.address and isinstance(order.address, dict):
            address = order.address.get("fullAddress", "Адрес не указан")
        else:
            address = "Адрес не указан"
        
        message = f"""
🆕 <b>Новый заказ FBS</b>

📦 <b>Артикул:</b> {order.article}
🆔 <b>ID заказа:</b> {order.order_id}
🔖 <b>UID:</b> {order.order_uid}
💰 <b>Цена продажи:</b> {order.sale_price:.2f} ₽
📅 <b>Дата продажи:</b> {order.seller_date}
📍 <b>Адрес:</b> {address}
🚚 <b>Тип доставки:</b> {order.delivery_type.upper()}
🆔 <b>RID:</b> {order.rid}
"""
        
        if order.nm_id:
            message += f"🔢 <b>nmId:</b> {order.nm_id}\n"
        if order.chrt_id:
            message += f"🔢 <b>chrtId:</b> {order.chrt_id}\n"
        if order.price:
            message += f"💵 <b>Цена:</b> {order.price:.2f} ₽\n"
        
        return message.strip()
    
    def send_order_notification(self, order) -> bool:
        """
        Отправляет уведомление о новом заказе
        
        Args:
            order: Объект Order
            
        Returns:
            bool: True если уведомление отправлено успешно, False иначе
        """
        message = self.format_order_notification(order)
        return self.send_message(message)
    
    def format_daily_statistics(self, orders_count: int, date: str = None) -> str:
        """
        Форматирует сообщение со статистикой за день
        
        Args:
            orders_count: Количество заказов за день
            date: Дата в формате YYYY-MM-DD (если None, используется сегодня)
            
        Returns:
            str: Отформатированное сообщение
        """
        import datetime
        
        if date is None:
            date_obj = datetime.datetime.utcnow().date()
        else:
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        
        date_str = date_obj.strftime('%d.%m.%Y')
        
        message = f"""
📊 <b>Статистика за {date_str}</b>

📦 <b>Всего заказов:</b> {orders_count}
"""
        
        if orders_count == 0:
            message += "\n😔 Заказов не было"
        elif orders_count == 1:
            message += "\n✅ Обработан 1 заказ"
        else:
            message += f"\n✅ Обработано заказов: {orders_count}"
        
        return message.strip()
    
    def send_daily_statistics(self, orders_count: int, date: str = None) -> bool:
        """
        Отправляет статистику за день
        
        Args:
            orders_count: Количество заказов за день
            date: Дата в формате YYYY-MM-DD (если None, используется сегодня)
            
        Returns:
            bool: True если сообщение отправлено успешно, False иначе
        """
        message = self.format_daily_statistics(orders_count, date)
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """
        Проверяет соединение с Telegram API
        
        Returns:
            bool: True если соединение успешно, False иначе
        """
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при проверке соединения с Telegram: {e}")
            return False
    
    def get_updates(self, timeout: int = 10) -> list:
        """
        Получает обновления от Telegram бота
        
        Args:
            timeout: Таймаут в секундах
            
        Returns:
            list: Список обновлений
        """
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": timeout
        }
        
        try:
            response = requests.get(url, params=params, timeout=timeout + 5)
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                updates = data.get("result", [])
                if updates:
                    self.last_update_id = max(update["update_id"] for update in updates)
                return updates
            return []
        except Exception as e:
            self.logger.error(f"Ошибка при получении обновлений: {e}")
            return []
    
    def wait_for_start_command(self, timeout: int = 60) -> Optional[str]:
        """
        Ожидает команду /start от пользователя и возвращает chat_id
        
        Args:
            timeout: Максимальное время ожидания в секундах
            
        Returns:
            Optional[str]: Chat ID пользователя или None
        """
        self.logger.info("Ожидание команды /start от пользователя...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            updates = self.get_updates(timeout=5)
            
            for update in updates:
                if "message" in update:
                    message = update["message"]
                    chat = message.get("chat", {})
                    text = message.get("text", "")
                    
                    if text == "/start":
                        chat_id = str(chat.get("id"))
                        self.chat_id = chat_id
                        self.send_message(
                            "✅ Бот активирован! Теперь вы будете получать уведомления о новых заказах FBS.",
                            chat_id=chat_id
                        )
                        return chat_id
            
            time.sleep(1)
        
        self.logger.warning("Таймаут ожидания команды /start")
        return None
