"""
Модуль для мониторинга заказов
"""
import time
import logging
import sys
from typing import Optional
from datetime import datetime, timedelta

from config import Config
from database import DatabaseManager
from api import WBAPIClient
from api.analytics_client import WBAnalyticsClient
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
        
        # Инициализация Analytics API и Content API (если указан ключ)
        analytics_api_key = config.wb_analytics_api_key or config.wb_api_key
        self.analytics_client = WBAnalyticsClient(analytics_api_key) if analytics_api_key else None
        
        # Content API для получения списка товаров (используется для лучшего отображения)
        from api.content_client import WBContentClient
        self.content_client = WBContentClient(config.wb_api_key) if config.wb_api_key else None
        
        # Получаем или устанавливаем chat_id
        self._initialize_chat_id()
        
        self.is_running = False
        self.last_daily_report_date = None  # Дата последнего отчета
        self.last_views_report_date = None  # Дата последнего отчета о просмотрах
    
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
            consecutive_errors = 0
            max_consecutive_errors = 5
            
            while self.is_running:
                try:
                    self._process_orders()
                    self._check_and_send_daily_report()
                    
                    # Сбрасываем счетчик ошибок при успешной итерации
                    consecutive_errors = 0
                    
                    # Форматируем время до следующей проверки
                    minutes = self.config.wb_poll_interval // 60
                    seconds = self.config.wb_poll_interval % 60
                    if minutes > 0:
                        if seconds > 0:
                            time_str = f"{minutes} мин {seconds} сек"
                        else:
                            time_str = f"{minutes} мин"
                    else:
                        time_str = f"{seconds} сек"
                    
                    self.logger.info(f"Следующая проверка через {time_str}")
                    sys.stdout.flush()  # Принудительный flush для демона
                    
                    # Защита от зависания: используем sleep с проверкой is_running
                    # Также проверяем время для ежедневного отчета каждую минуту
                    sleep_interval = 1  # Проверяем каждую секунду
                    total_slept = 0
                    last_report_check = 0  # Время последней проверки отчета (в секундах)
                    
                    while total_slept < self.config.wb_poll_interval and self.is_running:
                        time.sleep(sleep_interval)
                        total_slept += sleep_interval
                        
                        # Проверяем ежедневный отчет каждую минуту (60 секунд)
                        # чтобы не пропустить момент 00:00
                        if total_slept - last_report_check >= 60:
                            self._check_and_send_daily_report()
                            last_report_check = total_slept
                    
                except Exception as e:
                    consecutive_errors += 1
                    self.logger.error(f"Ошибка в цикле мониторинга (ошибка {consecutive_errors}/{max_consecutive_errors}): {e}", exc_info=True)
                    sys.stdout.flush()
                    sys.stderr.flush()
                    
                    # Если слишком много ошибок подряд, останавливаемся
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.critical(f"Превышено максимальное количество последовательных ошибок ({max_consecutive_errors}). Остановка монитора.")
                        self.stop()
                        break
                    
                    # Небольшая задержка перед следующей попыткой
                    time.sleep(10)
                    
        except KeyboardInterrupt:
            self.logger.info("Получен сигнал остановки")
            sys.stdout.flush()
            self.stop()
        except Exception as e:
            self.logger.error(f"Критическая ошибка в мониторе: {e}", exc_info=True)
            sys.stdout.flush()
            sys.stderr.flush()
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
            sys.stdout.flush()  # Принудительный flush для демона
            
            orders = self.wb_client.get_new_orders()
            
            new_orders_count = 0
            for order in orders:
                if not self.db_manager.is_order_processed(order.order_uid):
                    # Отправляем уведомление с retry-логикой
                    if self.telegram_bot.send_order_notification(order):
                        # Помечаем заказ как обработанный
                        self.db_manager.mark_order_as_processed(
                            order.order_uid,
                            order.order_id,
                            order.created_at
                        )
                        new_orders_count += 1
                        self.logger.info(f"Новый заказ обработан: {order.order_uid}")
                        sys.stdout.flush()
                    else:
                        self.logger.warning(f"Не удалось отправить уведомление для заказа: {order.order_uid}")
                        sys.stdout.flush()
                else:
                    self.logger.debug(f"Заказ {order.order_uid} уже был обработан")
            
            if new_orders_count > 0:
                self.logger.info(f"Обработано новых заказов: {new_orders_count}")
            else:
                self.logger.info("Новых заказов не обнаружено")
            
            sys.stdout.flush()
                
        except Exception as e:
            self.logger.error(f"Ошибка при обработке заказов: {e}", exc_info=True)
            sys.stdout.flush()
            sys.stderr.flush()
    
    def _check_and_send_daily_report(self) -> None:
        """Проверяет время и отправляет ежедневные отчеты в 00:00 и 00:05"""
        now = datetime.utcnow()
        current_date = now.date()
        
        # Отчет о заказах в 00:00-00:05
        if now.hour == 0 and now.minute <= 5:
            self.logger.debug(f"Проверка времени для отчета о заказах: {now.hour}:{now.minute:02d}")
            # Отправляем отчет только один раз за день
            if self.last_daily_report_date != current_date:
                # Получаем статистику за вчерашний день
                yesterday = current_date - timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y-%m-%d')
                orders_count = self.db_manager.get_orders_count_for_date(yesterday_str)
                
                # Отправляем статистику с retry-логикой
                self.logger.info(f"Отправка ежедневной статистики за {yesterday_str}: {orders_count} заказов")
                sys.stdout.flush()
                if self.telegram_bot.send_daily_statistics(orders_count, yesterday_str):
                    self.logger.info("Ежедневная статистика успешно отправлена")
                else:
                    self.logger.warning("Не удалось отправить ежедневную статистику")
                sys.stdout.flush()
                
                # Обновляем дату последнего отчета
                self.last_daily_report_date = current_date
        
        # Отчет о просмотрах карточек в 00:05-00:10
        if now.hour == 0 and 5 <= now.minute <= 10:
            self.logger.debug(f"Проверка времени для отчета о просмотрах: {now.hour}:{now.minute:02d}, last_report_date: {self.last_views_report_date}, current_date: {current_date}")
            
            # Проверяем, что analytics_client инициализирован
            if not self.analytics_client:
                if self.last_views_report_date != current_date:
                    self.logger.warning("Analytics API клиент не инициализирован. Отчет о просмотрах не будет отправлен.")
                    self.last_views_report_date = current_date  # Помечаем как обработанное, чтобы не спамить
                return
            
            # Отправляем отчет только один раз за день
            if self.last_views_report_date != current_date:
                self.logger.debug(f"Время для отправки отчета о просмотрах! last_report_date: {self.last_views_report_date}, current_date: {current_date}")
                # Получаем статистику просмотров за вчерашний день
                yesterday = current_date - timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y-%m-%d')
                
                try:
                    self.logger.info(f"Получение статистики просмотров за {yesterday_str}")
                    sys.stdout.flush()
                    
                    # Используем новый endpoint для получения детализированной статистики
                    views_stats = self.analytics_client.get_product_views_detailed_for_date(yesterday_str, nm_ids=None)
                    
                    if views_stats:
                        self.logger.info(f"Отправка отчета о просмотрах за {yesterday_str}: {len(views_stats)} карточек")
                        sys.stdout.flush()
                        if self.telegram_bot.send_product_views_report(views_stats, yesterday_str):
                            self.logger.info("Отчет о просмотрах успешно отправлен")
                        else:
                            self.logger.warning("Не удалось отправить отчет о просмотрах")
                    else:
                        self.logger.info(f"Нет просмотров за {yesterday_str}, отчет не отправляется")
                    sys.stdout.flush()
                    
                    # Обновляем дату последнего отчета (вне зависимости от наличия просмотров)
                    self.last_views_report_date = current_date
                except Exception as e:
                    self.logger.error(f"Ошибка при получении/отправке отчета о просмотрах: {e}", exc_info=True)
                    sys.stdout.flush()
                    sys.stderr.flush()
        else:
            # Сбрасываем дату отчета, если уже не время отчета (после 00:10)
            if now.hour != 0 or now.minute > 10:
                if self.last_daily_report_date == current_date:
                    self.last_daily_report_date = None
                if self.last_views_report_date == current_date:
                    self.last_views_report_date = None
    
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
