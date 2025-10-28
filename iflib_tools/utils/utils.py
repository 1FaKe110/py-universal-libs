from __future__ import annotations
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Any, Generator, Dict, Optional
from loguru import logger


class DataUtils:
    """Утилиты для работы с данными"""

    @staticmethod
    def chunker(sequence: List[Any], chunk_size: int) -> Generator[List[Any], None, None]:
        """Разбивает последовательность на чанки"""
        for i in range(0, len(sequence), chunk_size):
            yield sequence[i:i + chunk_size]

    @staticmethod
    def date_range(start_date: str, end_date: str, date_format: str = "%Y-%m-%d") -> List[datetime]:
        """Генерирует диапазон дат"""
        start = datetime.strptime(start_date, date_format)
        end = datetime.strptime(end_date, date_format)

        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)

        return dates

    @staticmethod
    def safe_json_loads(data: str, default: Any = None) -> Any:
        """Безопасный парсинг JSON"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def df_to_records(df: pd.DataFrame) -> List[Dict]:
        """Конвертирует DataFrame в список словарей"""
        if df.empty:
            return []
        return df.replace({pd.NA: None}).to_dict('records')


class ValidationUtils:
    """Утилиты валидации"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Проверяет валидность email"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Проверяет валидность номера телефона"""
        import re
        # Базовая проверка российских номеров
        pattern = r'^(\+7|7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
        return bool(re.match(pattern, phone))


class FormatUtils:
    """Утилиты форматирования"""

    @staticmethod
    def format_bytes(size_bytes: int) -> str:
        """Форматирует размер в байтах"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Форматирует длительность"""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:.0f}m {seconds:.0f}s"


# Создание экземпляров утилит
data_utils = DataUtils()
validation_utils = ValidationUtils()
format_utils = FormatUtils()