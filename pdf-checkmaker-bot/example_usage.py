"""
Пример использования генератора PDF-чеков для Telegram бота (aiogram).
"""

import asyncio
import logging
from pathlib import Path

from src.pdf_generator import generate_receipt_pdf

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def handle_files(csv_file_path: str, html_file_path: str, receipt_id: str = None):
    """
    Обработка файлов и генерация PDF-чека.

    Args:
        csv_file_path: Путь к CSV файлу
        html_file_path: Путь к HTML шаблону
        receipt_id: ID чека (опционально)
    """
    try:
        # Читаем файлы
        with open(csv_file_path, "rb") as f:
            csv_bytes = f.read()
        
        with open(html_file_path, "rb") as f:
            html_bytes = f.read()
        
        # Генерируем PDF
        pdf_bytes, error = generate_receipt_pdf(
            data_bytes=csv_bytes,
            html_template_bytes=html_bytes,
            receipt_id=receipt_id or "AUTO-001",
            file_type=None  # Автоопределение
        )
        
        if error:
            print(f"Ошибка: {error}")
            return None
        
        # Сохраняем PDF
        output_path = f"receipt_{receipt_id or 'AUTO-001'}.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"PDF успешно создан: {output_path}")
        return pdf_bytes
        
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return None


async def example_aiogram_handler():
    """
    Пример обработчика для aiogram бота.
    """
    # Имитация получения файлов от пользователя
    # В реальном боте это будет через message.document
    
    csv_path = "tests/test_files/sample.csv"
    html_path = "tests/test_files/sample.html"
    
    pdf_bytes = await handle_files(
        csv_file_path=csv_path,
        html_file_path=html_path,
        receipt_id="BOT-001"
    )
    
    if pdf_bytes:
        # В реальном боте отправляем PDF пользователю:
        # await bot.send_document(chat_id, document=io.BytesIO(pdf_bytes), filename="receipt.pdf")
        print(f"PDF готов к отправке, размер: {len(pdf_bytes)} байт")


def example_sync_usage():
    """
    Пример синхронного использования.
    """
    from pathlib import Path
    
    # Читаем тестовые файлы
    csv_path = Path("tests/test_files/sample.csv")
    html_path = Path("tests/test_files/sample.html")
    
    if not csv_path.exists() or not html_path.exists():
        print("Тестовые файлы не найдены!")
        return
    
    csv_bytes = csv_path.read_bytes()
    html_bytes = html_path.read_bytes()
    
    # Генерируем PDF
    pdf_bytes, error = generate_receipt_pdf(
        data_bytes=csv_bytes,
        html_template_bytes=html_bytes,
        receipt_id="SYNC-001",
        file_type=None
    )
    
    if error:
        print(f"Ошибка: {error}")
        return
    
    # Сохраняем
    output_path = Path("example_receipt.pdf")
    output_path.write_bytes(pdf_bytes)
    print(f"PDF сохранен: {output_path}")


if __name__ == "__main__":
    print("=== Пример синхронного использования ===")
    example_sync_usage()
    
    print("\n=== Пример асинхронного использования ===")
    asyncio.run(example_aiogram_handler())




