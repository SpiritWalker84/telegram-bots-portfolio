"""
Пакет для работы с API
"""
from .wb_client import WBAPIClient, Order
from .analytics_client import WBAnalyticsClient
from .content_client import WBContentClient

__all__ = ["WBAPIClient", "Order", "WBAnalyticsClient", "WBContentClient"]
