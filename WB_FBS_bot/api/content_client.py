"""
Модуль для работы с Content API Wildberries (получение списка карточек товаров)
"""
import requests
import logging
from typing import List, Dict, Optional
import time


class WBContentClient:
    """Класс для работы с Content API Wildberries"""
    
    def __init__(self, api_key: str):
        """
        Инициализация клиента Content API
        
        Args:
            api_key: API ключ для авторизации
        """
        self.api_key = api_key
        self.base_url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_all_cards(self, max_retries: int = 3, retry_delay: int = 10) -> List[Dict]:
        """
        Получает список всех карточек товаров продавца с пагинацией
        
        Args:
            max_retries: Максимальное количество попыток для каждого запроса
            retry_delay: Задержка между попытками в секундах
            
        Returns:
            List[Dict]: Список всех карточек товаров
        """
        all_cards = []
        cursor = {
            "limit": 100
        }
        
        while True:
            payload = {
                "settings": {
                    "cursor": cursor,
                    "filter": {
                        "withPhoto": -1
                    }
                }
            }
            
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.debug(f"Запрос карточек (попытка {attempt}/{max_retries}), limit: {cursor.get('limit', 100)}")
                    response = self.session.post(self.base_url, json=payload, timeout=30)
                    response.raise_for_status()
                    
                    data = response.json()
                    cards = data.get("cards", [])
                    cursor_info = data.get("cursor", {})
                    
                    all_cards.extend(cards)
                    
                    self.logger.debug(f"Получено карточек: {len(cards)}, всего: {len(all_cards)}")
                    
                    # Проверяем, нужно ли продолжать пагинацию
                    total = cursor_info.get("total", 0)
                    limit = cursor.get("limit", 100)
                    
                    if total < limit or not cursor_info.get("nmID"):
                        # Все карточки получены
                        self.logger.info(f"Получено всех карточек: {len(all_cards)}")
                        return all_cards
                    
                    # Обновляем cursor для следующей итерации
                    cursor = {
                        "updatedAt": cursor_info.get("updatedAt"),
                        "nmID": cursor_info.get("nmID"),
                        "limit": 100
                    }
                    
                    break  # Успешно получили данные, выходим из retry цикла
                    
                except requests.exceptions.Timeout:
                    self.logger.warning(f"Таймаут при запросе карточек (попытка {attempt}/{max_retries})")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    else:
                        raise
                except requests.exceptions.ConnectionError as e:
                    self.logger.warning(f"Ошибка соединения (попытка {attempt}/{max_retries}): {e}")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    else:
                        raise
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Ошибка при запросе карточек (попытка {attempt}/{max_retries}): {e}")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    else:
                        raise
        
        return all_cards
    
    def get_vendor_codes_list(self) -> List[str]:
        """
        Получает список всех vendorCode из карточек товаров
        
        Returns:
            List[str]: Список vendorCode (отсортированный, уникальный)
        """
        cards = self.get_all_cards()
        vendor_codes = []
        
        for card in cards:
            vendor_code = card.get("vendorCode", "").strip()
            if vendor_code:
                vendor_codes.append(vendor_code)
        
        # Удаляем дубликаты и сортируем
        unique_vendor_codes = sorted(list(set(vendor_codes)))
        self.logger.info(f"Получено уникальных vendorCode: {len(unique_vendor_codes)}")
        
        return unique_vendor_codes
