"""
Парсер файлов CSV/JSON/Excel с автоопределением формата и кодировки.
"""

import io
import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def detect_file_type(data_bytes: bytes) -> str:
    """
    Автоматическое определение типа файла по содержимому.

    Args:
        data_bytes: Байты файла

    Returns:
        Тип файла: "csv", "json" или "xlsx"
    """
    if not data_bytes:
        return "csv"
    
    # Excel файлы начинаются с ZIP заголовка (PK)
    if data_bytes.startswith(b"PK"):
        return "xlsx"
    
    # JSON файлы начинаются с { или [
    first_char = data_bytes.lstrip()[:1]
    if first_char in (b"{", b"["):
        return "json"
    
    # По умолчанию CSV
    return "csv"


def parse_csv(data_bytes: bytes, encoding: str = None) -> List[Dict[str, Any]]:
    """
    Парсинг CSV файла с поддержкой различных кодировок.

    Args:
        data_bytes: Байты CSV файла
        encoding: Кодировка (если None, пробует автоматически)

    Returns:
        Список словарей с данными

    Raises:
        ValueError: Если не удалось распарсить файл
    """
    encodings = encoding and [encoding] or ["utf-8", "cp1251", "windows-1251", "utf-8-sig"]
    
    for enc in encodings:
        try:
            text = data_bytes.decode(enc)
            df = pd.read_csv(io.StringIO(text), encoding=enc)
            
            # Преобразуем DataFrame в список словарей
            records = df.to_dict("records")
            
            # Нормализуем данные
            normalized = []
            for record in records:
                normalized_record = {}
                for key, value in record.items():
                    # Очищаем ключи от пробелов
                    clean_key = str(key).strip()
                    normalized_record[clean_key] = value
                normalized.append(normalized_record)
            
            logger.info(f"CSV успешно распарсен с кодировкой {enc}, строк: {len(normalized)}")
            if normalized:
                logger.debug(f"Первый элемент: {normalized[0]}")
                logger.debug(f"Ключи: {list(normalized[0].keys())}")
            return normalized
            
        except UnicodeDecodeError:
            logger.debug(f"Ошибка декодирования с кодировкой {enc}, пробуем следующую...")
            continue
        except Exception as e:
            logger.error(f"Ошибка парсинга CSV с кодировкой {enc}: {e}")
            if enc == encodings[-1]:  # Последняя попытка
                raise ValueError(f"Не удалось распарсить CSV файл: {e}")
            continue
    
    raise ValueError("Не удалось определить кодировку CSV файла")


def parse_json(data_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Парсинг JSON файла.

    Args:
        data_bytes: Байты JSON файла

    Returns:
        Список словарей с данными

    Raises:
        ValueError: Если не удалось распарсить файл
    """
    try:
        import json
        
        text = data_bytes.decode("utf-8")
        data = json.loads(text)
        
        # Если это список, возвращаем как есть
        if isinstance(data, list):
            return data
        
        # Если это словарь, оборачиваем в список
        if isinstance(data, dict):
            return [data]
        
        raise ValueError(f"Неожиданный тип данных в JSON: {type(data)}")
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга JSON: {e}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Ошибка декодирования JSON (ожидается UTF-8): {e}")
    except Exception as e:
        raise ValueError(f"Не удалось распарсить JSON файл: {e}")


def parse_xlsx(data_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Парсинг Excel файла (.xlsx).

    Args:
        data_bytes: Байты Excel файла

    Returns:
        Список словарей с данными

    Raises:
        ValueError: Если не удалось распарсить файл
    """
    try:
        df = pd.read_excel(io.BytesIO(data_bytes), engine="openpyxl")
        
        # Преобразуем DataFrame в список словарей
        records = df.to_dict("records")
        
        # Нормализуем данные
        normalized = []
        for record in records:
            normalized_record = {}
            for key, value in record.items():
                clean_key = str(key).strip()
                normalized_record[clean_key] = value
            normalized.append(normalized_record)
        
        logger.info(f"Excel успешно распарсен, строк: {len(normalized)}")
        return normalized
        
    except Exception as e:
        raise ValueError(f"Не удалось распарсить Excel файл: {e}")


def parse_file(data_bytes: bytes, file_type: str = None) -> List[Dict[str, Any]]:
    """
    Универсальный парсер файлов с автоопределением типа.

    Args:
        data_bytes: Байты файла
        file_type: Тип файла ("csv", "json", "xlsx") или None для автоопределения

    Returns:
        Список словарей с данными

    Raises:
        ValueError: Если не удалось распарсить файл
    """
    if not data_bytes:
        raise ValueError("Пустой файл")
    
    # Автоопределение типа файла
    if file_type is None:
        file_type = detect_file_type(data_bytes)
        logger.info(f"Автоопределен тип файла: {file_type}")
    
    file_type = file_type.lower()
    
    if file_type == "csv":
        return parse_csv(data_bytes)
    elif file_type == "json":
        return parse_json(data_bytes)
    elif file_type == "xlsx":
        return parse_xlsx(data_bytes)
    else:
        raise ValueError(f"Неподдерживаемый тип файла: {file_type}")

