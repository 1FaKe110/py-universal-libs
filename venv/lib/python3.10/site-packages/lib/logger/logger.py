from __future__ import annotations
import sys
import re
import json
from typing import Any, Dict, Optional
from loguru import logger


class LogFormatter:
    """Форматирование логов"""

    @staticmethod
    def mask_sensitive_data(value: str) -> str:
        """Маскирует чувствительные данные"""
        if not value:
            return ""

        # Маска URL с паролями
        if '://' in value and '@' in value:
            return re.sub(r'://(.*?):(.*?)@', r'://\1:****@', value)

        # Маска токенов
        if len(value) > 10:
            if any(keyword in value.lower() for keyword in ['token', 'key', 'secret']):
                return f"{'*' * (len(value) - 6)}{value[-6:]}"

        return value

    @staticmethod
    def format_extra(extra: Dict) -> str:
        """Форматирует дополнительные поля"""
        if not extra:
            return ""

        lines = []
        for key, value in extra.items():
            if value is None or value == "":
                continue

            # Сериализуем значение в JSON для вложенных структур
            try:
                if isinstance(value, (dict, list)):
                    # Используем компактный JSON без отступов
                    display_value = json.dumps(value, ensure_ascii=False)
                else:
                    display_value = str(value)

                # Применяем маскирование к строковому представлению
                display_value = LogFormatter.mask_sensitive_data(display_value)

                # Обрезаем слишком длинные значения
                if len(display_value) > 100:
                    display_value = display_value[:97] + "..."

                # Экранируем фигурные скобки для предотвращения KeyError
                display_value = display_value.replace('{', '{{').replace('}', '}}')

                lines.append(f"    - {key}: {display_value}")
            except Exception as e:
                # Если не удалось сериализовать, используем repr
                display_value = repr(value)
                if len(display_value) > 100:
                    display_value = display_value[:97] + "..."
                # Экранируем фигурные скобки
                display_value = display_value.replace('{', '{{').replace('}', '}}')
                lines.append(f"    - {key}: {display_value}")

        return "\n" + "\n".join(lines) if lines else ""


class LoggerSetup:
    """Настройка логгера"""

    def __init__(self, level: str = "INFO", enable_file_logging: bool = False):
        self.level = level
        self.enable_file_logging = enable_file_logging
        self.setup_logger()

    def setup_logger(self):
        """Настраивает логгер"""
        logger.remove()

        # Консольный вывод
        logger.add(
            sys.stdout,
            format=self._console_format,
            level=self.level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )

        # Файловый вывод
        if self.enable_file_logging:
            logger.add(
                "logs/app_{time:YYYY-MM-DD}.log",
                level="DEBUG",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
                rotation="10 MB",
                retention="7 days",
                compression="zip"
            )

        logger.info("Logger setup completed")

    def _console_format(self, record):
        """Формат для консоли"""
        # Экранируем message, чтобы предотвратить KeyError
        message = record["message"].replace('{', '{{').replace('}', '}}')

        prefix = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            f"<level>{message}</level>"
        )

        extra_str = LogFormatter.format_extra(record["extra"])
        return prefix + extra_str + "\n"


class AppLogger:
    """Основной класс логгера приложения"""

    def __init__(self, name: str = "app", **default_extra):
        self.name = name
        self.default_extra = default_extra

    def info(self, message: str, **extra):
        """Логирование информации"""
        all_extra = {**self.default_extra, **extra}
        logger.bind(**all_extra).info(message)

    def error(self, message: str, error: Optional[Exception] = None, **extra):
        """Логирование ошибок"""
        all_extra = {
            **self.default_extra,
            "error_type": error.__class__.__name__ if error else None,
            "error_msg": str(error) if error else None,
            **extra
        }

        logger.bind(**all_extra).error(message)
        if error:
            logger.opt(exception=error).debug("Stack trace")

    def debug(self, message: str, **extra):
        """Логирование отладочной информации"""
        all_extra = {**self.default_extra, **extra}
        logger.bind(**all_extra).debug(message)

    def warning(self, message: str, **extra):
        """Логирование предупреждений"""
        all_extra = {**self.default_extra, **extra}
        logger.bind(**all_extra).warning(message)


# Инициализация по умолчанию
log_setup = LoggerSetup()
app_logger = AppLogger()