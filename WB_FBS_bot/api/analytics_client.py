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
        self.base_url_grouped = "https://seller-analytics-api.wildberries.ru/api/analytics/v3/sales-funnel/grouped/history"
        self.base_url_products = "https://seller-analytics-api.wildberries.ru/api/analytics/v3/sales-funnel/products/history"
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
        
        # Формируем запрос для одного дня
        payload = {
            "selectedPeriod": {
                "start": date,
                "end": date
            },
            "skipDeletedNm": False,
            "aggregationLevel": "day"
        }
        
        # Пробуем разные варианты для получения детализации
        # Вариант 1: groupBySa (не работает - API все равно возвращает агрегированные данные)
        # payload["groupBySa"] = True
        
        # Вариант 2: передача nmIds для фильтрации (может помочь получить детализацию)
        if nm_ids and len(nm_ids) > 0:
            payload["nmIds"] = nm_ids
            self.logger.debug(f"Используется фильтрация по nmIds: {len(nm_ids)} товаров")
        
        self.logger.debug(f"Payload запроса (первые 200 символов): {str(payload)[:200]}")
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Запрос статистики просмотров за {date} (попытка {attempt}/{max_retries})")
                response = self.session.post(self.base_url_grouped, json=payload, timeout=30)
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
    
    def get_product_views_detailed_for_date(self, date: str = None, nm_ids: Optional[List[int]] = None, max_retries: int = 3, retry_delay: int = 10) -> Dict[str, int]:
        """
        Получает детализированную статистику просмотров карточек товаров за указанную дату
        Использует endpoint /products/history для получения данных с vendorCode
        
        Args:
            date: Дата в формате YYYY-MM-DD (если None, используется сегодня)
            nm_ids: Опциональный список nmId для фильтрации (если None или пустой, запрашивает все товары)
            max_retries: Максимальное количество попыток
            retry_delay: Задержка между попытками в секундах
            
        Returns:
            Dict[str, int]: Словарь {vendorCode: openCount}, только с ненулевыми значениями
        """
        import time
        
        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Нужны реальные nmIds для запроса (до 20 артикулов за раз)
        if not nm_ids or len(nm_ids) == 0:
            self.logger.warning("nmIds не указаны. Нужно получить список товаров через Content API.")
            return {}
        
        # Ограничиваем до 20 артикулов за запрос (лимит API)
        if len(nm_ids) > 20:
            self.logger.warning(f"Слишком много nmIds ({len(nm_ids)}), используем первые 20")
            nm_ids = nm_ids[:20]
        
        # Формируем запрос с selectedPeriod (как требует API)
        payload = {
            "nmIds": nm_ids,
            "selectedPeriod": {
                "start": date,
                "end": date
            },
            "skipDeletedNm": True,
            "aggregationLevel": "day"
        }
        
        self.logger.debug(f"Запрос для {len(nm_ids)} товаров за {date}")
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Запрос детализированной статистики просмотров за {date} (попытка {attempt}/{max_retries})")
                
                # Используем только рабочий URL (seller-analytics-api)
                # analytics-api.wildberries.ru не существует
                response = None
                last_error = None
                
                try:
                    response = self.session.post(self.base_url_products, json=payload, timeout=30)
                    
                    # Обработка rate limiting (429)
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 30))
                        self.logger.warning(f"Rate limit (429), ждем {retry_after} секунд...")
                        time.sleep(retry_after)
                        # Продолжаем в цикле попыток
                        if attempt < max_retries:
                            continue
                        else:
                            last_error = f"Status 429: Rate limit exceeded"
                            self.logger.error(f"Превышен лимит запросов после {max_retries} попыток")
                    elif response.status_code != 200:
                        last_error = f"Status {response.status_code}: {response.text[:200]}"
                        self.logger.warning(f"Ошибка при запросе к API: {last_error}")
                except Exception as e:
                    last_error = str(e)
                    self.logger.warning(f"Исключение при запросе к API: {e}")
                
                if not response or response.status_code != 200:
                    error_msg = last_error or f"Status {response.status_code if response else 'None'}"
                    self.logger.error(f"Не удалось получить успешный ответ от API: {error_msg}")
                    raise requests.exceptions.RequestException(f"API вернул ошибку: {error_msg}")
                response.raise_for_status()
                
                response.raise_for_status()
                
                # Ответ в формате {"data": [...]} или просто массив
                response_data = response.json()
                
                # Проверяем структуру ответа
                if isinstance(response_data, dict) and "data" in response_data:
                    data = response_data["data"]
                elif isinstance(response_data, list):
                    data = response_data
                else:
                    self.logger.error(f"Неожиданная структура ответа: {type(response_data)}")
                    return {}
                
                self.logger.debug(f"Полный ответ API (первые 500 символов): {str(data)[:500]}")
                self.logger.debug(f"Получено записей в ответе: {len(data)}")
                
                # Структура ответа: [{"product": {...}, "history": [...]}]
                # где history содержит записи с openCount за даты
                views_stats = {}
                
                for product_data in data:
                    product = product_data.get("product", {})
                    vendor_code = product.get("vendorCode", "").strip()
                    nm_id = product.get("nmId")
                    history = product_data.get("history", [])
                    
                    # Если нет vendorCode, используем nmId как идентификатор
                    if not vendor_code and nm_id:
                        vendor_code = f"nmId_{nm_id}"
                    elif not vendor_code:
                        self.logger.debug(f"Пропущен продукт без vendorCode и nmId")
                        continue
                    
                    if not history:
                        self.logger.debug(f"Продукт {vendor_code} без истории")
                        continue
                    
                    # Ищем данные за указанную дату в history
                    for day_data in history:
                        day_date = day_data.get("date")
                        if day_date == date:
                            # Используем openCount (может быть также shows в некоторых случаях)
                            open_count = day_data.get("openCount", day_data.get("shows", 0))
                            
                            self.logger.debug(f"Продукт {vendor_code}, дата {day_date}, openCount: {open_count}")
                            
                            if open_count > 0:
                                if vendor_code in views_stats:
                                    views_stats[vendor_code] += open_count
                                else:
                                    views_stats[vendor_code] = open_count
                            break
                
                self.logger.info(f"Обработано записей: {len(data)}, с просмотрами: {len(views_stats)}")
                
                return views_stats
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Таймаут при запросе к Analytics API (попытка {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    raise
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"Ошибка соединения с Analytics API (попытка {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Ошибка при запросе к Analytics API (попытка {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
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
