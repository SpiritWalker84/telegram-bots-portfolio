"""Точка входа для Flask сервера."""
import logging
from flask import Flask
try:
    from flask_cors import CORS
except ImportError:
    # Если flask-cors не установлен, создаем заглушку
    class CORS:
        def __init__(self, app):
            @app.after_request
            def after_request(response):
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
                return response

from src.config import Config
from src.server.routes import ServerRoutes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Создать и настроить Flask приложение.
    
    Returns:
        Настроенное Flask приложение
    """
    app = Flask(__name__)
    CORS(app)  # Разрешаем CORS для работы с фронтендом
    
    try:
        # Инициализация конфигурации
        config = Config()
        logger.info("Конфигурация загружена успешно")
        
        # Инициализация маршрутов
        server_routes = ServerRoutes(app, config)
        logger.info("Маршруты зарегистрированы")
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации приложения: {e}")
        raise
    
    return app


if __name__ == '__main__':
    app = create_app()
    logger.info("Flask сервер запущен на http://localhost:5000")
    app.run(debug=True, port=5000)
