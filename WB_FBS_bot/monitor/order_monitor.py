"""
Модуль для мониторинга заказов
"""
import time
import logging
from typing import Optional
from datetime import datetime

from config import Config
from database import DatabaseManager
from api import WBAPIClient
from telegram import TelegramBot


class OrderMonitor:
    """Класс для мониторинга новых заказов и отправки уведомлений"""
    
    def __init__(self, config: Config):
        """
        Инициализация монитора заказов
        
        Args:
            config: Объект конфигурации
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Инициализация компонентов
        self.db_manager = DatabaseManager(config.db_path)
        self.wb_client = WBAPIClient(config.wb_api_key, config.wb_api_url)
        self.telegram_bot = TelegramBot(config.telegram_bot_token, config.telegram_chat_id)
        
        # Получаем или устанавливаем chat_id
        self._initialize_chat_id()
        
        self.is_running = False
    
    def _initialize_chat_id(self) -> None:
        """Инициализирует chat_id из БД или получает его от пользователя"""
        # Сначала проверяем сохраненный chat_id в БД
        saved_chat_id = self.db_manager.get_setting("telegram_chat_id")
        
        if saved_chat_id:
            self.telegram_bot.chat_id = saved_chat_id
            self.logger.info(f"Используется сохраненный chat_id: {saved_chat_id}")
        elif self.config.telegram_chat_id:
            # Если указан в конфиге, используем его и сохраняем
            self.telegram_bot.chat_id = self.config.telegram_chat_id
            self.db_manager.set_setting("telegram_chat_id", self.config.telegram_chat_id)
            self.logger.info(f"Используется chat_id из конфигурации: {self.config.telegram_chat_id}")
        else:
            # Пытаемся получить chat_id от пользователя
            self.logger.info("Chat ID не найден. Ожидание команды /start...")
            chat_id = self.telegram_bot.wait_for_start_command(timeout=60)
            if chat_id:
                self.db_manager.set_setting("telegram_chat_id", chat_id)
                self.logger.info(f"Chat ID получен и сохранен: {chat_id}")
            else:
                self.logger.warning("Не удалось получить chat_id. Бот будет работать только при наличии сохраненного chat_id.")
    
    def start(self) -> None:
        """Запускает мониторинг заказов"""
        self.logger.info("Запуск мониторинга заказов")
        
        # Проверяем наличие chat_id
        if not self.telegram_bot.chat_id:
            self.logger.error("Chat ID не установлен. Отправьте команду /start боту и перезапустите приложение.")
            return
        
        self.is_running = True
        
        # Проверка соединений
        if not self._check_connections():
            self.logger.error("Не удалось установить соединения. Проверьте конфигурацию.")
            return
        
        try:
            while self.is_running:
                self._process_orders()
                self.logger.info(f"Ожидание {self.config.wb_poll_interval} секунд до следующей проверки...")
                time.sleep(self.config.wb_poll_interval)
        except KeyboardInterrupt:
            self.logger.info("Получен сигнал остановки")
            self.stop()
        except Exception as e:
            self.logger.error(f"Критическая ошибка в мониторе: {e}")
            raise
    
    def stop(self) -> None:
        """Останавливает мониторинг заказов"""
        self.logger.info("Остановка мониторинга заказов")
        self.is_running = False
    
    def _check_connections(self) -> bool:
        """
        Проверяет соединения с внешними сервисами
        
        Returns:
            bool: True если все соединения успешны, False иначе
        """
        self.logger.info("Проверка соединений...")
        
        wb_ok = self.wb_client.test_connection()
        telegram_ok = self.telegram_bot.test_connection()
        
        if wb_ok and telegram_ok:
            self.logger.info("Все соединения установлены успешно")
            return True
        else:
            self.logger.error(f"WB API: {'OK' if wb_ok else 'FAILED'}, "
                            f"Telegram: {'OK' if telegram_ok else 'FAILED'}")
            return False
    
    def _process_orders(self) -> None:
        """Обрабатывает новые заказы"""
        try:
            self.logger.info("Проверка новых заказов...")
            orders = self.wb_client.get_new_orders()
            
            new_orders_count = 0
            for order in orders:
                if not self.db_manager.is_order_processed(order.order_uid):
                    # Отправляем уведомление
                    if self.telegram_bot.send_order_notification(order):
                        # Помечаем заказ как обработанный
                        self.db_manager.mark_order_as_processed(
                            order.order_uid,
                            order.order_id,
                            order.created_at
                        )
                        new_orders_count += 1
                        self.logger.info(f"Новый заказ обработан: {order.order_uid}")
                    else:
                        self.logger.warning(f"Не удалось отправить уведомление для заказа: {order.order_uid}")
                else:
                    self.logger.debug(f"Заказ {order.order_uid} уже был обработан")
            
            if new_orders_count > 0:
                self.logger.info(f"Обработано новых заказов: {new_orders_count}")
            else:
                self.logger.info("Новых заказов не обнаружено")
                
        except Exception as e:
            self.logger.error(f"Ошибка при обработке заказов: {e}")
    
    def get_statistics(self) -> dict:
        """
        Возвращает статистику работы монитора
        
        Returns:
            dict: Словарь со статистикой
        """
        return {
            "processed_orders_count": self.db_manager.get_processed_orders_count(),
            "is_running": self.is_running,
            "poll_interval": self.config.wb_poll_interval
        }
