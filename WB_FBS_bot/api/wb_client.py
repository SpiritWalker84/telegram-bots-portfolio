"""
Модуль для работы с API Wildberries
"""
import requests
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Order:
    """Класс для представления заказа"""
    order_uid: str
    order_id: int
    article: str
    created_at: str
    sale_price: float
    delivery_type: str
    address: Dict
    seller_date: str
    rid: str
    nm_id: Optional[int] = None
    chrt_id: Optional[int] = None
    price: Optional[float] = None
    final_price: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Order":
        """
        Создает объект Order из словаря
        
        Args:
            data: Словарь с данными заказа из API
            
        Returns:
            Order: Объект заказа
        """
        return cls(
            order_uid=data.get("orderUid", ""),
            order_id=data.get("id", 0),
            article=data.get("article", ""),
            created_at=data.get("createdAt", ""),
            sale_price=data.get("salePrice", 0) / 100 if data.get("salePrice") else 0,  # Конвертация из копеек
            delivery_type=data.get("deliveryType", ""),
            address=data.get("address", {}),
            seller_date=data.get("sellerDate", ""),
            rid=data.get("rid", ""),
            nm_id=data.get("nmId"),
            chrt_id=data.get("chrtId"),
            price=data.get("price", 0) / 100 if data.get("price") else None,
            final_price=data.get("finalPrice", 0) / 100 if data.get("finalPrice") else None
        )


class WBAPIClient:
    """Класс для работы с API Wildberries"""
    
    def __init__(self, api_key: str, api_url: str):
        """
        Инициализация клиента API
        
        Args:
            api_key: API ключ для авторизации
            api_url: URL эндпоинта API
        """
        self.api_key = api_key
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_new_orders(self) -> List[Order]:
        """
        Получает список новых заказов FBS
        
        Returns:
            List[Order]: Список новых заказов
            
        Raises:
            requests.RequestException: При ошибке запроса к API
        """
        try:
            self.logger.info(f"Запрос новых заказов: {self.api_url}")
            response = self.session.get(self.api_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            orders_data = data.get("orders", [])
            
            # Фильтруем только FBS заказы
            fbs_orders = [
                order_data for order_data in orders_data
                if order_data.get("deliveryType", "").lower() == "fbs"
            ]
            
            orders = [Order.from_dict(order_data) for order_data in fbs_orders]
            self.logger.info(f"Получено {len(orders)} новых FBS заказов")
            
            return orders
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка при запросе к API WB: {e}")
            raise
        except KeyError as e:
            self.logger.error(f"Неожиданная структура ответа API: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при обработке ответа API: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Проверяет соединение с API
        
        Returns:
            bool: True если соединение успешно, False иначе
        """
        try:
            self.get_new_orders()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при проверке соединения: {e}")
            return False
