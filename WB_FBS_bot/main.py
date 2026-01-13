"""
Точка входа приложения для мониторинга заказов FBS с Wildberries
"""
import logging
import sys
from config import Config
from monitor import OrderMonitor


def setup_logging() -> None:
    """Настройка логирования с принудительным flush для демона"""
    # Создаем кастомный handler с flush
    class FlushingStreamHandler(logging.StreamHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()
    
    class FlushingFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            FlushingStreamHandler(sys.stdout),
            FlushingFileHandler('wb_fbs_bot.log', encoding='utf-8')
        ],
        force=True  # Перезаписываем существующую конфигурацию
    )
    
    # Принудительный flush для stdout
    sys.stdout.flush()
    sys.stderr.flush()


def main():
    """Основная функция приложения"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Загрузка конфигурации
        logger.info("Загрузка конфигурации...")
        config = Config.from_env()
        logger.info("Конфигурация загружена успешно")
        
        # Создание и запуск монитора
        monitor = OrderMonitor(config)
        logger.info("Монитор заказов инициализирован")
        
        # Запуск мониторинга
        monitor.start()
        
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        logger.error("Убедитесь, что установлены все необходимые переменные окружения в файле .env:")
        logger.error("  - WB_API_KEY")
        logger.error("  - TELEGRAM_BOT_TOKEN")
        logger.error("  - TELEGRAM_CHAT_ID (опционально, будет получен автоматически)")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
