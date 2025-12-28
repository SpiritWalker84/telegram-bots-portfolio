"""
Основной модуль для генерации PDF-чеков из файлов данных и HTML шаблонов.
"""

import io
import logging
from typing import Tuple, Union

from pypdf import PdfWriter
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from .file_parser import parse_file
from .template_renderer import render_template

logger = logging.getLogger(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def generate_receipt_pdf(
    data_bytes: bytes,
    html_template_bytes: bytes,
    receipt_id: str = None,
    file_type: str = None
) -> Tuple[Union[bytes, None], Union[str, None]]:
    """
    Генерирует PDF-чек из файла данных (CSV/JSON/Excel) и HTML шаблона.

    Args:
        data_bytes: Байты файла с данными (CSV/JSON/Excel)
        html_template_bytes: Байты HTML шаблона
        receipt_id: ID чека (опционально)
        file_type: Тип файла ("csv", "json", "xlsx") или None для автоопределения

    Returns:
        Tuple[pdf_bytes, error_msg]:
            - pdf_bytes: Байты PDF файла или None при ошибке
            - error_msg: Сообщение об ошибке или None при успехе
    """
    try:
        # Парсим файл с данными
        logger.info("Начало парсинга файла данных...")
        data = parse_file(data_bytes, file_type)
        
        if not data:
            return None, "Файл данных пуст или не содержит записей"
        
        # Декодируем HTML шаблон
        try:
            html_template = html_template_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Пробуем другие кодировки
            try:
                html_template = html_template_bytes.decode("cp1251")
            except UnicodeDecodeError:
                return None, "Не удалось декодировать HTML шаблон (ожидается UTF-8 или CP1251)"
        
        # Рендерим шаблон
        logger.info("Рендеринг HTML шаблона...")
        
        # Если данных больше одной строки, генерируем отдельный PDF для каждой страницы
        # и объединяем их, чтобы каждая страница была полностью независимой (с рамками)
        if len(data) > 1:
            logger.info(f"Генерация {len(data)} отдельных PDF страниц...")
            font_config = FontConfiguration()
            pdf_writer = PdfWriter()
            
            # Генерируем отдельный PDF для каждой строки данных
            for idx, row_data in enumerate(data):
                # Рендерим шаблон для одной строки
                row_receipt_id = f"{receipt_id or 'RECEIPT'}-{idx + 1}" if receipt_id else f"RECEIPT-{idx + 1}"
                rendered_html = render_template(html_template, [row_data], row_receipt_id, one_page_per_row=False)
                
                # Генерируем PDF для этой страницы
                html_doc = HTML(string=rendered_html)
                page_pdf_bytes = html_doc.write_pdf(font_config=font_config)
                
                # Добавляем страницу в объединенный PDF
                page_pdf_reader = io.BytesIO(page_pdf_bytes)
                pdf_writer.append(page_pdf_reader)
                logger.info(f"Страница {idx + 1}/{len(data)} сгенерирована")
            
            # Объединяем все страницы в один PDF
            output_pdf = io.BytesIO()
            pdf_writer.write(output_pdf)
            pdf_bytes = output_pdf.getvalue()
            
            logger.info(f"PDF успешно сгенерирован, размер: {len(pdf_bytes)} байт ({len(data)} страниц)")
        else:
            # Стандартный режим: один PDF для всех данных
            rendered_html = render_template(html_template, data, receipt_id, one_page_per_row=False)
            
            # Генерируем PDF
            logger.info("Генерация PDF...")
            font_config = FontConfiguration()
            html_doc = HTML(string=rendered_html)
            pdf_bytes = html_doc.write_pdf(font_config=font_config)
            
            logger.info(f"PDF успешно сгенерирован, размер: {len(pdf_bytes)} байт")
        
        return pdf_bytes, None
        
    except ValueError as e:
        error_msg = f"Ошибка парсинга данных: {str(e)}"
        logger.error(error_msg)
        return None, error_msg
        
    except Exception as e:
        error_msg = f"Неожиданная ошибка при генерации PDF: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, error_msg

