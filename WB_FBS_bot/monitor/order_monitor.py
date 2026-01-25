"""
Модуль для мониторинга заказов
"""
import time
import logging
import sys
from typing import Optional
from datetime import datetime, timedelta, timezone

from config import Config
from database import DatabaseManager
from api import WBAPIClient
from api.analytics_client import WBAnalyticsClient
from telegram import TelegramBot

# Московское время (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))


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
        if analytics_api_key:
            self.analytics_client = WBAnalyticsClient(analytics_api_key)
            self.logger.info("Analytics API клиент инициализирован")
        else:
            self.analytics_client = None
            self.logger.warning("Analytics API ключ не найден. Отчет о просмотрах карточек не будет доступен.")
        
        # Content API для получения списка товаров (используется для лучшего отображения)
        from api.content_client import WBContentClient
        self.content_client = WBContentClient(config.wb_api_key) if config.wb_api_key else None
        
        # Получаем или устанавливаем chat_id
        self._initialize_chat_id()
        
        self.is_running = False
        self._report_sending_lock = False  # Блокировка для предотвращения параллельной отправки
    
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
                    # Проверяем время для ежедневного отчета только в нужные моменты
                    sleep_interval = 1  # Проверяем каждую секунду
                    total_slept = 0
                    last_report_check = 0  # Время последней проверки отчета (в секундах)
                    
                    # Первая проверка времени сразу
                    self._check_and_send_daily_report()
                    
                    while total_slept < self.config.wb_poll_interval and self.is_running:
                        time.sleep(sleep_interval)
                        total_slept += sleep_interval
                        
                        # Проверяем ежедневный отчет только в критические моменты:
                        # - каждую секунду в первые 10 секунд часов 00:00 и 05:00
                        # - каждые 30 секунд в остальное время
                        current_check_time = datetime.now(MSK_TIMEZONE)
                        should_check = False
                        
                        if (current_check_time.hour in [0, 5] and current_check_time.minute == 0 and current_check_time.second < 10):
                            # В критическое время проверяем каждую секунду
                            should_check = True
                        elif total_slept - last_report_check >= 30:
                            # В остальное время проверяем каждые 30 секунд
                            should_check = True
                        
                        if should_check:
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
                try:
                    # Проверяем, был ли заказ обработан (с retry-логикой)
                    if not self.db_manager.is_order_processed(order.order_uid):
                        # Отправляем уведомление с retry-логикой
                        if self.telegram_bot.send_order_notification(order):
                            # Помечаем заказ как обработанный (с retry-логикой)
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
                except Exception as e:
                    # Ошибка при обработке одного заказа - логируем и продолжаем
                    self.logger.warning(
                        f"Ошибка при обработке заказа {order.order_uid}: {e}. "
                        f"Заказ будет обработан при следующей проверке."
                    )
                    sys.stdout.flush()
                    continue
            
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
        """Проверяет время и отправляет ежедневные отчеты в 00:00 и 05:00 (московское время)"""
        # Используем московское время (UTC+3)
        now = datetime.now(MSK_TIMEZONE)
        current_date = now.date()
        current_date_str = current_date.strftime('%Y-%m-%d')
        current_time_str = now.strftime('%H:%M:%S')
        current_hour = now.hour
        current_minute = now.minute
        current_second = now.second
        
        # Блокировка для предотвращения параллельной отправки
        if self._report_sending_lock:
            self.logger.debug(f"Блокировка активна, пропускаем проверку отчетов. Время: {current_time_str}")
            return
        
        # Логируем только если мы близко к времени отправки (для отладки)
        if (current_hour == 0 and current_minute == 0) or (current_hour == 5 and current_minute == 0):
            self.logger.debug(f"Проверка времени для отчетов. Время: {current_time_str}, час={current_hour}, мин={current_minute}, сек={current_second}")
        
        # СТРОГАЯ проверка: отчет о заказах ТОЛЬКО в 00:00:00-00:00:05 (московское время)
        if now.hour == 0 and now.minute == 0 and 0 <= now.second < 5:
            # Проверяем в БД, был ли уже отправлен отчет за сегодня
            last_report_date = self.db_manager.get_setting("last_daily_report_date")
            if last_report_date == current_date_str:
                # Отчет уже был отправлен сегодня - выходим
                self.logger.debug(f"Отчет о заказах уже отправлен сегодня ({current_date_str}). Время: {current_time_str}")
                return
            
            # Атомарно проверяем и устанавливаем дату в БД (только если еще не установлена)
            if not self.db_manager.set_setting_if_not_exists("last_daily_report_date", current_date_str):
                # Дата уже была установлена другим процессом - выходим
                self.logger.debug(f"Другой процесс уже обрабатывает отчет о заказах. Время: {current_time_str}")
                return
            
            # Устанавливаем блокировку СРАЗУ
            self._report_sending_lock = True
            try:
                self.logger.info(f"Начало отправки ежедневной статистики заказов. Время: {current_time_str}")
                sys.stdout.flush()
                
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
                    # При ошибке отправки удаляем дату, чтобы можно было повторить
                    self.db_manager.set_setting("last_daily_report_date", "")
                sys.stdout.flush()
            except Exception as e:
                self.logger.error(f"Ошибка при отправке ежедневной статистики: {e}", exc_info=True)
                # При ошибке удаляем дату, чтобы можно было повторить
                self.db_manager.set_setting("last_daily_report_date", "")
                sys.stdout.flush()
                sys.stderr.flush()
            finally:
                # Снимаем блокировку после отправки
                self._report_sending_lock = False
        
        # СТРОГАЯ проверка: отчет о просмотрах ТОЛЬКО в 05:00:00-05:00:05 (московское время)
        elif now.hour == 5 and now.minute == 0 and 0 <= now.second < 5:
            # Проверяем в БД, был ли уже отправлен отчет за сегодня
            last_views_report_date = self.db_manager.get_setting("last_views_report_date")
            if last_views_report_date == current_date_str:
                # Отчет уже был отправлен сегодня - выходим
                self.logger.debug(f"Отчет о просмотрах уже отправлен сегодня ({current_date_str}). Время: {current_time_str}")
                return
            
            # Проверяем, что analytics_client инициализирован
            if not self.analytics_client:
                # Сохраняем дату, чтобы не пытаться снова
                self.db_manager.set_setting("last_views_report_date", current_date_str)
                self.logger.warning("Analytics API клиент не инициализирован. Отчет о просмотрах не будет отправлен.")
                return
            
            # Атомарно проверяем и устанавливаем дату в БД (только если еще не установлена)
            if not self.db_manager.set_setting_if_not_exists("last_views_report_date", current_date_str):
                # Дата уже была установлена другим процессом - выходим
                self.logger.debug(f"Другой процесс уже обрабатывает отчет о просмотрах. Время: {current_time_str}")
                return
            
            # Устанавливаем блокировку СРАЗУ
            self._report_sending_lock = True
            try:
                self.logger.info(f"Начало отправки отчета о просмотрах. Дата: {current_date_str}, Время: {current_time_str}")
                sys.stdout.flush()
                
                # Получаем статистику просмотров за вчерашний день
                yesterday = current_date - timedelta(days=1)
                yesterday_str = yesterday.strftime('%Y-%m-%d')
                
                self.logger.info(f"Получение статистики просмотров за {yesterday_str}")
                sys.stdout.flush()
                
                # Получаем список товаров для запроса (API требует nmIds, до 20 за раз)
                nm_ids = None
                nm_to_vendor = {}
                content_api_failed = False
                
                if self.content_client:
                        try:
                            self.logger.warning("Получение списка товаров для запроса статистики...")
                            cards = self.content_client.get_all_cards()
                            nm_ids = [card.get("nmID") for card in cards if card.get("nmID")]
                            self.logger.warning(f"Получено {len(nm_ids)} nmIds")
                            
                            # Создаем маппинг nmId -> vendorCode для замены в отчете
                            nm_to_vendor = {card.get("nmID"): card.get("vendorCode", "").strip() 
                                          for card in cards if card.get("nmID") and card.get("vendorCode")}
                        except Exception as e:
                            self.logger.error(f"Не удалось получить список товаров через Content API: {e}")
                            content_api_failed = True
                            # Пробуем использовать кеш или пропускаем отчет
                            if not nm_ids:
                                self.logger.error("Невозможно получить отчет без списка товаров. Отправляем уведомление об ошибке.")
                                self.telegram_bot.send_message(f"⚠️ Ошибка при получении отчета о просмотрах за {yesterday_str}: не удалось получить список товаров через Content API. Ошибка: {str(e)[:200]}")
                                # Выходим из внутреннего try, но дата уже обновлена
                                raise  # Пробрасываем ошибку наверх
                    else:
                        self.logger.error("Content API клиент не инициализирован, невозможно получить список товаров")
                        self.telegram_bot.send_message(f"⚠️ Ошибка: Content API клиент не инициализирован. Отчет о просмотрах за {yesterday_str} не может быть получен.")
                        # Выходим из внутреннего try, но дата уже обновлена
                        raise Exception("Content API клиент не инициализирован")
                    
                if not nm_ids or len(nm_ids) == 0:
                    self.logger.warning(f"Список товаров пуст, отчет не может быть сформирован")
                    raise Exception("Список товаров пуст")
                
                # Если товаров больше 20, делаем несколько запросов батчами
                batch_size = 20
                total_batches = (len(nm_ids) + batch_size - 1) // batch_size
                
                if len(nm_ids) > batch_size:
                        self.logger.warning(f"Товаров: {len(nm_ids)}, делаем запросы батчами по {batch_size} (всего {total_batches} батчей)")
                        all_views_stats = {}
                        
                        for i in range(0, len(nm_ids), batch_size):
                            batch_nm_ids = nm_ids[i:i+batch_size]
                            batch_num = (i // batch_size) + 1
                            
                            # Увеличиваем задержку между батчами для избежания rate limiting
                            if i >= batch_size:
                                delay = 10  # Увеличено с 5 до 10 секунд
                                self.logger.warning(f"Задержка {delay} секунд перед батчем {batch_num}...")
                                time.sleep(delay)
                            
                            try:
                                self.logger.warning(f"Запрос батча {batch_num}/{total_batches} ({len(batch_nm_ids)} товаров)...")
                                batch_stats = self.analytics_client.get_product_views_detailed_for_date(yesterday_str, nm_ids=batch_nm_ids)
                                
                                # Объединяем результаты батча
                                for key, value in batch_stats.items():
                                    if key.startswith("nmId_"):
                                        nm_id = int(key.replace("nmId_", ""))
                                        vendor_code = nm_to_vendor.get(nm_id)
                                        if vendor_code:
                                            all_views_stats[vendor_code] = all_views_stats.get(vendor_code, 0) + value
                                        else:
                                            all_views_stats[key] = all_views_stats.get(key, 0) + value
                                    else:
                                        all_views_stats[key] = all_views_stats.get(key, 0) + value
                                
                                # Логируем прогресс
                                total_views_found = sum(all_views_stats.values())
                                batch_views = sum(batch_stats.values())
                                if batch_views > 0:
                                    self.logger.warning(f"В батче {batch_num} найдено: {batch_views} просмотров (всего: {total_views_found})")
                            except Exception as batch_error:
                                self.logger.error(f"Ошибка при обработке батча {batch_num}: {batch_error}")
                                # Продолжаем со следующим батчем
                                continue
                        
                    views_stats = all_views_stats
                else:
                    views_stats = self.analytics_client.get_product_views_detailed_for_date(yesterday_str, nm_ids=nm_ids)
                    
                    # Заменяем nmId_* на vendorCode
                    final_stats = {}
                    for key, value in views_stats.items():
                        if key.startswith("nmId_"):
                            nm_id = int(key.replace("nmId_", ""))
                            vendor_code = nm_to_vendor.get(nm_id, key)
                            final_stats[vendor_code] = value
                        else:
                            final_stats[key] = value
                    views_stats = final_stats
                
                if views_stats:
                    self.logger.warning(f"Отправка отчета о просмотрах за {yesterday_str}: {len(views_stats)} карточек")
                    sys.stdout.flush()
                    if self.telegram_bot.send_product_views_report(views_stats, yesterday_str):
                        self.logger.warning("Отчет о просмотрах успешно отправлен")
                    else:
                        self.logger.error("Не удалось отправить отчет о просмотрах")
                        # При ошибке отправки удаляем дату, чтобы можно было повторить
                        self.db_manager.set_setting("last_views_report_date", "")
                else:
                    self.logger.warning(f"Нет просмотров за {yesterday_str}, отчет не отправляется")
                sys.stdout.flush()
                
                # Дата уже обновлена в начале блока, здесь только логируем
                self.logger.debug(f"Дата последнего отчета о просмотрах: {current_date_str}")
                except Exception as e:
                    # Обработка ошибок на верхнем уровне
                    self.logger.error(f"Критическая ошибка при обработке отчета о просмотрах: {e}", exc_info=True)
                    sys.stdout.flush()
                    sys.stderr.flush()
                    # При ошибке удаляем дату, чтобы можно было повторить попытку
                    self.db_manager.set_setting("last_views_report_date", "")
                finally:
                    # Снимаем блокировку после отправки
                    self._report_sending_lock = False
        else:
            # Не время для отправки отчетов - выходим без действий
            # Логируем только если мы близко к времени отправки (для отладки)
            if (now.hour == 0 and now.minute == 0) or (now.hour == 5 and now.minute == 0):
                if now.second >= 5:
                    self.logger.debug(f"Время для отчетов прошло. Текущее время: {current_time_str}")
    
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
