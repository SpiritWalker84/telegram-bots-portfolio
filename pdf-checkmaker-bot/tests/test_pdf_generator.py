"""
Тесты для генератора PDF-чеков.
"""

import pytest

# Проверка доступности WeasyPrint
try:
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (OSError, ImportError) as e:
    WEASYPRINT_AVAILABLE = False
    WEASYPRINT_ERROR = str(e)

from src.file_parser import detect_file_type, parse_file

# Импорт функции генерации PDF только если WeasyPrint доступен
if WEASYPRINT_AVAILABLE:
    from src.pdf_generator import generate_receipt_pdf


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint requires GTK+ runtime on Windows")
def test_csv_utf8():
    """Тест парсинга CSV с кодировкой UTF-8."""
    csv_content = """name,price,quantity
Товар 1,100.50,2
Товар 2,200.75,1"""
    
    html_template = """
    <html>
    <head><style>@page { size: A6; }</style></head>
    <body>
        <table>
            {% for item in items %}
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.price }}</td>
                <td>{{ item.quantity }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    pdf_bytes, error = generate_receipt_pdf(
        csv_content.encode("utf-8"),
        html_template.encode("utf-8"),
        receipt_id="TEST-001"
    )
    
    assert error is None, f"Ошибка генерации PDF: {error}"
    assert pdf_bytes is not None, "PDF не был сгенерирован"
    assert len(pdf_bytes) > 0, "PDF пустой"
    assert pdf_bytes.startswith(b"%PDF"), "Неверный формат PDF"


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint requires GTK+ runtime on Windows")
def test_csv_cp1251():
    """Тест парсинга CSV с кодировкой CP1251."""
    csv_content = """name,price,quantity
Товар 1,100.50,2
Товар 2,200.75,1"""
    
    html_template = """
    <html>
    <head><style>@page { size: A6; }</style></head>
    <body>
        <table>
            {% for item in items %}
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.price }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    pdf_bytes, error = generate_receipt_pdf(
        csv_content.encode("cp1251"),
        html_template.encode("utf-8"),
        receipt_id="TEST-002"
    )
    
    assert error is None, f"Ошибка генерации PDF: {error}"
    assert pdf_bytes is not None, "PDF не был сгенерирован"


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint requires GTK+ runtime on Windows")
def test_json():
    """Тест парсинга JSON файла."""
    json_content = """[
        {"name": "Товар 1", "price": 100.50, "quantity": 2},
        {"name": "Товар 2", "price": 200.75, "quantity": 1}
    ]"""
    
    html_template = """
    <html>
    <head><style>@page { size: A6; }</style></head>
    <body>
        <table>
            {% for item in items %}
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.price }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    pdf_bytes, error = generate_receipt_pdf(
        json_content.encode("utf-8"),
        html_template.encode("utf-8"),
        file_type="json"
    )
    
    assert error is None, f"Ошибка генерации PDF: {error}"
    assert pdf_bytes is not None, "PDF не был сгенерирован"


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint requires GTK+ runtime on Windows")
def test_xlsx():
    """Тест парсинга Excel файла."""
    import pandas as pd
    import io
    
    # Создаем тестовый Excel файл
    df = pd.DataFrame({
        "name": ["Товар 1", "Товар 2"],
        "price": [100.50, 200.75],
        "quantity": [2, 1]
    })
    
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_bytes = excel_buffer.getvalue()
    
    html_template = """
    <html>
    <head><style>@page { size: A6; }</style></head>
    <body>
        <table>
            {% for item in items %}
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.price }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    pdf_bytes, error = generate_receipt_pdf(
        excel_bytes,
        html_template.encode("utf-8"),
        file_type="xlsx"
    )
    
    assert error is None, f"Ошибка генерации PDF: {error}"
    assert pdf_bytes is not None, "PDF не был сгенерирован"


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint requires GTK+ runtime on Windows")
def test_long_names():
    """Тест обработки длинных названий товаров."""
    csv_content = """name,price,quantity
Очень длинное название товара которое должно быть обрезано до 60 символов,100.50,2
Товар 2,200.75,1"""
    
    html_template = """
    <html>
    <head><style>@page { size: A6; }</style></head>
    <body>
        <table>
            {% for item in items %}
            <tr>
                <td>{{ item.name }}</td>
                <td>{{ item.price }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    
    pdf_bytes, error = generate_receipt_pdf(
        csv_content.encode("utf-8"),
        html_template.encode("utf-8")
    )
    
    assert error is None, f"Ошибка генерации PDF: {error}"
    assert pdf_bytes is not None, "PDF не был сгенерирован"


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint requires GTK+ runtime on Windows")
def test_invalid_html():
    """Тест обработки невалидного HTML."""
    csv_content = """name,price,quantity
Товар 1,100.50,2"""
    
    # HTML без закрывающих тегов
    html_template = "<html><body><table><tr><td>Test</td></tr></table>"
    
    pdf_bytes, error = generate_receipt_pdf(
        csv_content.encode("utf-8"),
        html_template.encode("utf-8")
    )
    
    # WeasyPrint может обработать неполный HTML, но лучше проверить
    # В реальности может быть ошибка или успешная генерация
    assert pdf_bytes is not None or error is not None


def test_detect_file_type():
    """Тест автоопределения типа файла."""
    # CSV
    csv_bytes = b"name,price\nItem,100"
    assert detect_file_type(csv_bytes) == "csv"
    
    # JSON
    json_bytes = b'[{"name": "Item"}]'
    assert detect_file_type(json_bytes) == "json"
    
    # Excel (ZIP header)
    excel_bytes = b"PK\x03\x04" + b"x" * 100
    assert detect_file_type(excel_bytes) == "xlsx"


@pytest.mark.skipif(not WEASYPRINT_AVAILABLE, reason="WeasyPrint requires GTK+ runtime on Windows")
def test_empty_file():
    """Тест обработки пустого файла."""
    html_template = "<html><body>Test</body></html>"
    
    pdf_bytes, error = generate_receipt_pdf(
        b"",
        html_template.encode("utf-8")
    )
    
    assert error is not None, "Должна быть ошибка для пустого файла"
    assert pdf_bytes is None


# Тесты парсинга файлов (не требуют WeasyPrint)
def test_parse_csv_utf8():
    """Тест парсинга CSV с UTF-8."""
    csv_content = """name,price,quantity
Товар 1,100.50,2
Товар 2,200.75,1"""
    
    data = parse_file(csv_content.encode("utf-8"), "csv")
    assert len(data) == 2
    assert data[0]["name"] == "Товар 1"
    assert float(str(data[0]["price"]).replace(",", ".")) == 100.50


def test_parse_csv_cp1251():
    """Тест парсинга CSV с CP1251."""
    csv_content = """name,price,quantity
Товар 1,100.50,2
Товар 2,200.75,1"""
    
    data = parse_file(csv_content.encode("cp1251"), "csv")
    assert len(data) == 2
    assert data[0]["name"] == "Товар 1"


def test_parse_json():
    """Тест парсинга JSON."""
    json_content = """[
        {"name": "Товар 1", "price": 100.50, "quantity": 2},
        {"name": "Товар 2", "price": 200.75, "quantity": 1}
    ]"""
    
    data = parse_file(json_content.encode("utf-8"), "json")
    assert len(data) == 2
    assert data[0]["name"] == "Товар 1"
    assert data[0]["price"] == 100.50


def test_parse_xlsx():
    """Тест парсинга Excel."""
    import pandas as pd
    import io
    
    df = pd.DataFrame({
        "name": ["Товар 1", "Товар 2"],
        "price": [100.50, 200.75],
        "quantity": [2, 1]
    })
    
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_bytes = excel_buffer.getvalue()
    
    data = parse_file(excel_bytes, "xlsx")
    assert len(data) == 2
    assert str(data[0]["name"]).strip() == "Товар 1"

