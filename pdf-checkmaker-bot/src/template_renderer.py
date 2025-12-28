"""
Рендеринг HTML шаблонов с Jinja2 и защитой верстки.
"""

import logging
from typing import Any, Dict, List

from jinja2 import Environment, BaseLoader, TemplateError

from .utils import truncate_text

logger = logging.getLogger(__name__)


def ensure_css_protection(html_content: str) -> str:
    """
    Добавляет защитные CSS стили если их нет в шаблоне.

    Args:
        html_content: Исходный HTML

    Returns:
        HTML с добавленными CSS стилями
    """
    # Проверяем наличие различных CSS правил
    has_table_layout = "table-layout" in html_content.lower()
    has_word_wrap = "word-wrap" in html_content.lower() or "overflow-wrap" in html_content.lower()
    has_text_overflow = "text-overflow" in html_content.lower()
    has_page_rule = "@page" in html_content.lower()
    
    # Если есть <style> тег, добавляем туда
    if "<style>" in html_content and "</style>" in html_content:
        style_end = html_content.find("</style>")
        additional_css = ""
        
        if not has_table_layout:
            additional_css += """
    table {
        table-layout: fixed;
        width: 100%;
        border-collapse: collapse;
    }
"""
        
        if not has_word_wrap:
            additional_css += """
    td, th {
        word-wrap: break-word;
        overflow-wrap: break-word;
        word-break: break-all;
        hyphens: auto;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 0;
        padding: 2px 4px;
        white-space: normal;
    }
"""
        
        if not has_page_rule:
            additional_css += """    @page { 
        size: A6; 
        margin: 5mm;
    }
    .page-break {
        page-break-after: always;
    }
"""
        
        if additional_css:
            html_content = (
                html_content[:style_end] 
                + additional_css 
                + html_content[style_end:]
            )
    else:
        # Создаем новый <style> блок
        additional_css = ""
        if not has_table_layout:
            additional_css += """
    table {
        table-layout: fixed;
        width: 100%;
        border-collapse: collapse;
    }
"""
        
        if not has_word_wrap:
            additional_css += """
    td, th {
        word-wrap: break-word;
        overflow-wrap: break-word;
        word-break: break-all;
        hyphens: auto;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 0;
        padding: 2px 4px;
        white-space: normal;
    }
"""
        
        if not has_page_rule:
            additional_css += """    @page { 
        size: A6; 
        margin: 5mm;
    }
    .page-break {
        page-break-after: always;
    }
"""
        
        if additional_css:
            # Вставляем перед </head> или перед </body>
            if "</head>" in html_content:
                html_content = html_content.replace(
                    "</head>",
                    f"<style>{additional_css}</style>\n</head>"
                )
            elif "<body>" in html_content:
                html_content = html_content.replace(
                    "<body>",
                    f"<head><style>{additional_css}</style></head>\n<body>"
                )
            else:
                # Добавляем в начало
                html_content = f"<style>{additional_css}</style>\n{html_content}"
    
    return html_content


def normalize_data_for_template(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Нормализует данные для шаблона: обрезает длинные тексты.

    Args:
        data: Список словарей с данными

    Returns:
        Нормализованные данные
    """
    normalized = []
    for record in data:
        normalized_record = {}
        for key, value in record.items():
            # Обрезаем длинные текстовые значения
            if isinstance(value, str) and len(value) > 60:
                normalized_record[key] = truncate_text(value, 60)
            else:
                normalized_record[key] = value
        normalized.append(normalized_record)
    
    return normalized


def render_template(
    html_template: str,
    data: List[Dict[str, Any]],
    receipt_id: str = None,
    one_page_per_row: bool = True
) -> str:
    """
    Рендерит HTML шаблон с данными используя Jinja2.

    Args:
        html_template: HTML шаблон (Jinja2)
        data: Данные для рендеринга
        receipt_id: ID чека (опционально)
        one_page_per_row: Если True и данных больше одной строки, каждая строка
                         рендерится на отдельной странице PDF

    Returns:
        Отрендеренный HTML

    Raises:
        TemplateError: Если ошибка рендеринга шаблона
    """
    try:
        # Нормализуем данные
        normalized_data = normalize_data_for_template(data)
        
        # Создаем Jinja2 окружение
        env = Environment(loader=BaseLoader())
        
        # Добавляем фильтры
        env.filters["truncate"] = truncate_text
        
        # Загружаем шаблон
        template = env.from_string(html_template)
        
        # Проверяем, есть ли в шаблоне цикл по items
        has_items_loop = "{% for" in html_template and "items" in html_template.lower()
        
        # Если one_page_per_row=True и нет цикла, рендерим каждую строку отдельно на отдельной странице
        if one_page_per_row and not has_items_loop and len(normalized_data) > 1:
            logger.info(f"Режим: одна страница на строку. Рендерим {len(normalized_data)} страниц")
            
            rendered_pages = []
            
            for idx, row_data in enumerate(normalized_data):
                # Контекст для текущей строки
                context = {
                    "items": [row_data],  # Одна строка как список
                    "receipt_id": f"{receipt_id or 'RECEIPT'}-{idx + 1}" if receipt_id else f"RECEIPT-{idx + 1}",
                    "total": float(str(row_data.get("price", 0)).replace(",", ".")) * float(str(row_data.get("quantity", 1)).replace(",", "."))
                    if row_data.get("price") is not None else 0
                }
                
                # Добавляем все поля текущей строки в контекст верхнего уровня
                for key, value in row_data.items():
                    if key not in context:
                        context[key] = value
                
                # Рендерим страницу
                page_html = template.render(**context)
                
                # Добавляем разрыв страницы после текущей страницы (кроме последней)
                if idx < len(normalized_data) - 1:
                    # Ищем закрывающий тег body или html
                    if "</body>" in page_html:
                        page_html = page_html.replace("</body>", '<div style="page-break-after: always;"></div></body>')
                    elif "</html>" in page_html:
                        page_html = page_html.replace("</html>", '<div style="page-break-after: always;"></div></html>')
                    else:
                        # Если нет структуры, добавляем в конец
                        page_html += '<div style="page-break-after: always;"></div>'
                
                rendered_pages.append(page_html)
            
            # Объединяем все страницы в один HTML документ
            # Каждая страница должна быть полностью независимым HTML документом
            # с правильными разрывами страниц между ними
            
            # Извлекаем head из первой страницы для общего документа
            first_page = rendered_pages[0]
            head_content = ""
            if "<head>" in first_page and "</head>" in first_page:
                head_start = first_page.find("<head>")
                head_end = first_page.find("</head>") + 7
                head_content = first_page[head_start:head_end]
                # Добавляем CSS для разрыва страниц
                if "page-break" not in head_content.lower():
                    page_break_style = """
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
"""
                    head_content = head_content.replace("</head>", page_break_style + "</head>")
            
            # Извлекаем содержимое body из каждой страницы
            # Каждая страница должна быть полностью независимой с фиксированной высотой
            page_bodies = []
            for idx, page_html in enumerate(rendered_pages):
                # Извлекаем содержимое body (без тегов body)
                if "<body>" in page_html and "</body>" in page_html:
                    body_start = page_html.find("<body>") + 6
                    body_end = page_html.find("</body>")
                    body_content = page_html[body_start:body_end].strip()
                else:
                    # Если нет body, берем весь контент
                    body_content = page_html.strip()
                
                # НЕ оборачиваем в контейнер, чтобы не нарушать структуру шаблона (рамки и т.д.)
                # Просто добавляем разрыв страницы в конце содержимого (кроме последней)
                if idx < len(rendered_pages) - 1:
                    # Добавляем невидимый элемент с разрывом страницы в самом конце
                    # Используем минимальный элемент, чтобы не нарушать верстку
                    body_content += '\n<div style="page-break-after: always; break-after: page; height: 0; margin: 0; padding: 0; line-height: 0; font-size: 0; visibility: hidden; overflow: hidden; border: none;"></div>'
                
                page_bodies.append(body_content)
            
            # Создаем объединенный HTML с одним body, содержащим все страницы
            page_bodies_str = '\n'.join(page_bodies)
            page_break_css = """
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
"""
            
            if head_content:
                combined_html = f"""<!DOCTYPE html>
<html>
{head_content}
<body>
{page_bodies_str}
</body>
</html>"""
            else:
                combined_html = """<!DOCTYPE html>
<html>
<head>""" + page_break_css + """
</head>
<body>
""" + page_bodies_str + """
</body>
</html>"""
            
            # Добавляем защиту верстки
            rendered = ensure_css_protection(combined_html)
            
            logger.info(f"Шаблон успешно отрендерен: {len(normalized_data)} страниц в одном PDF")
            return rendered
        
        # Стандартный режим: один шаблон для всех данных
        # Контекст для шаблона
        context = {
            "items": normalized_data,
            "receipt_id": receipt_id or "",
            "total": sum(
                float(str(item.get("price", 0)).replace(",", ".")) * float(str(item.get("quantity", 1)).replace(",", "."))
                for item in normalized_data
                if item.get("price") is not None
            )
        }
        
        # Если есть данные, добавляем все поля первого элемента в контекст верхнего уровня
        # Это позволяет использовать {{invoice_number}} вместо {{items[0].invoice_number}}
        # Это полезно для шаблонов, где один счет с данными в первой строке
        if normalized_data and len(normalized_data) > 0:
            first_item = normalized_data[0]
            # Добавляем все ключи первого элемента в контекст
            for key, value in first_item.items():
                # Не перезаписываем существующие ключи (items, receipt_id, total)
                if key not in context:
                    context[key] = value
        
        # Логируем данные для отладки
        logger.info(f"Контекст для шаблона: {len(normalized_data)} элементов")
        if normalized_data:
            logger.debug(f"Первый элемент данных: {normalized_data[0]}")
            logger.debug(f"Ключи первого элемента: {list(normalized_data[0].keys())}")
            logger.debug(f"Добавлены переменные верхнего уровня: {[k for k in normalized_data[0].keys() if k not in ['items', 'receipt_id', 'total']]}")
            if has_items_loop:
                logger.info(f"Обнаружен цикл по items в шаблоне - будут использованы все {len(normalized_data)} строк")
            else:
                logger.info(f"Цикл по items не найден - используются данные из первой строки")
        
        # Рендерим
        rendered = template.render(**context)
        
        # Добавляем защиту верстки
        rendered = ensure_css_protection(rendered)
        
        logger.info(f"Шаблон успешно отрендерен, элементов: {len(normalized_data)}")
        return rendered
        
    except TemplateError as e:
        logger.error(f"Ошибка рендеринга шаблона: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при рендеринге: {e}")
        raise TemplateError(f"Неожиданная ошибка при рендеринге: {e}") from e

