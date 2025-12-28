"""
Receipt PDF Generator - Генератор PDF-чеков из CSV/JSON/Excel + HTML шаблонов.
"""

__version__ = "1.0.0"

# Ленивый импорт для избежания ошибок при отсутствии GTK+ на Windows
def __getattr__(name):
    if name == "generate_receipt_pdf":
        from .pdf_generator import generate_receipt_pdf
        return generate_receipt_pdf
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["generate_receipt_pdf", "__version__"]

