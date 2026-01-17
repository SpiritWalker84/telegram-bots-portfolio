"""
Модуль для работы с Analytics API Wildberries
"""
import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class WBAnalyticsClient:
    """Класс для работы с Analytics API Wildberries"""
    
    def __init__(self, api_key: str):
        """
        Инициализация клиента Analytics API
        
        Args:
            api_key: API ключ для авторизации
        """
        self.api_key = api_key
        self.base_url = "https://seller-analytics-api.wildberries.ru/api/analytics/v3/sales-funnel/grouped/history"
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_product_views_for_date(self, date: str = None, nm_ids: Optional[List[int]] = None, max_retries: int = 3, retry_delay: int = 10) -> Dict[str, int]:
        """
        Получает количество просмотров карточек товаров за указанную дату
        
        Args:
            date: Дата в формате YYYY-MM-DD (если None, используется сегодня)
            nm_ids: Опциональный список nmId для фильтрации (может помочь получить детализацию)
            max_retries: Максимальное количество попыток
            retry_delay: Задержка между попытками в секундах
            
        Returns:
            Dict[str, int]: Словарь {vendorCode: openCount}, только с ненулевыми значениями
        """
        import time
        
        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Формируем запрос для одного дня с группировкой по vendorCode
        payload = {
            "selectedPeriod": {
                "start": date,
                "end": date
            },
            "skipDeletedNm": False,
            "aggregationLevel": "day"
        }
        
        # Пробуем разные варианты параметра группировки
        # Вариант 1: groupBySa (может не работать)
        payload["groupBySa"] = True
        
        # Если указаны nmIds, добавляем их для фильтрации
        if nm_ids and len(nm_ids) > 0:
            payload["nmIds"] = nm_ids
            self.logger.debug(f"Используется фильтрация по nmIds: {len(nm_ids)} товаров")
        
        self.logger.debug(f"Payload запроса: {payload}")
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Запрос статистики просмотров за {date} (попытка {attempt}/{max_retries})")
                response = self.session.post(self.base_url, json=payload, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                products_data = data.get("data", [])
                
                self.logger.debug(f"Полный ответ API (первые 500 символов): {str(data)[:500]}")
                self.logger.debug(f"Получено продуктов в ответе: {len(products_data)}")
                
                # Собираем статистику просмотров
                views_stats = {}
                total_products = 0
                products_with_history = 0
                
                for product_data in products_data:
                    total_products += 1
                    product = product_data.get("product", {})
                    vendor_code = product.get("vendorCode", "").strip()
                    nm_id = product.get("nmId")
                    history = product_data.get("history", [])
                    
                    if not history:
                        self.logger.debug(f"Продукт без истории: nmId={nm_id}, vendorCode={vendor_code}")
                        continue
                    
                    products_with_history += 1
                    
                    # Берем данные за указанную дату
                    for day_data in history:
                        day_date = day_data.get("date")
                        if day_date == date:
                            open_count = day_data.get("openCount", 0)
                            
                            # Если vendorCode пустой, используем nmId или "Общее"
                            if not vendor_code:
                                if nm_id and nm_id > 0:
                                    identifier = f"nmId_{nm_id}"
                                else:
                                    # Агрегированные данные - показываем как "Общее"
                                    identifier = "Общее"
                            else:
                                identifier = vendor_code
                            
                            self.logger.debug(f"Продукт {identifier}, дата {day_date}, openCount: {open_count}")
                            
                            if open_count > 0:
                                # Если уже есть запись с таким идентификатором, суммируем
                                if identifier in views_stats:
                                    views_stats[identifier] += open_count
                                else:
                                    views_stats[identifier] = open_count
                            break
                    else:
                        # Если не нашли данные за нужную дату
                        identifier = vendor_code or (f"nmId_{nm_id}" if nm_id else "N/A")
                        self.logger.debug(f"Продукт {identifier} - нет данных за {date}, доступные даты: {[d.get('date') for d in history]}")
                
                self.logger.info(f"Обработано продуктов: {total_products}, с историей: {products_with_history}, с просмотрами: {len(views_stats)}")
                
                if len(views_stats) == 0 and products_with_history > 0:
                    # Логируем пример данных для отладки
                    if products_data:
                        example_product = products_data[0]
                        self.logger.debug(f"Пример структуры продукта: nmId={example_product.get('product', {}).get('nmId')}, "
                                        f"история: {len(example_product.get('history', []))} записей")
                        if example_product.get('history'):
                            example_history = example_product.get('history')[0]
                            self.logger.debug(f"Пример записи истории: {example_history}")
                
                return views_stats
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Таймаут при запросе к Analytics API (попытка {attempt}/{max_retries})")
                if attempt < max_retries:
                    self.logger.info(f"Повторная попытка через {retry_delay} секунд...")
                    time.sleep(retry_delay)
                else:
                    raise
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"Ошибка соединения с Analytics API (попытка {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    self.logger.info(f"Повторная попытка через {retry_delay} секунд...")
                    time.sleep(retry_delay)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Ошибка при запросе к Analytics API (попытка {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    self.logger.info(f"Повторная попытка через {retry_delay} секунд...")
                    time.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                self.logger.error(f"Неожиданная ошибка при обработке ответа Analytics API: {e}")
                raise
        
        return {}
    
    def test_connection(self) -> bool:
        """
        Проверяет соединение с Analytics API
        
        Returns:
            bool: True если соединение успешно, False иначе
        """
        try:
            # Пробуем получить данные за вчерашний день
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
            self.get_product_views_for_date(yesterday)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при проверке соединения с Analytics API: {e}")
            return False
