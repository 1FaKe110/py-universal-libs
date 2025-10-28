from __future__ import annotations
import os
from urllib.parse import quote_plus

import yaml
from typing import Any, Dict, List, Optional, Type, TypeVar
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

T = TypeVar('T')


class DynamicConfig:
    """Динамический класс конфигурации, который позволяет произвольные атрибуты"""

    def __init__(self, data: Dict[str, Any] = None):
        self._data = data or {}
        # Преобразуем вложенные словари в DynamicConfig
        for key, value in self._data.items():
            if isinstance(value, dict):
                self._data[key] = DynamicConfig(value)
            elif isinstance(value, list):
                self._data[key] = [DynamicConfig(item) if isinstance(item, dict) else item for item in value]

    def __getattr__(self, name: str) -> Any:
        """Получение атрибута"""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __getitem__(self, name: str) -> Any:
        """Получение элемента как из словаря"""
        return self._data.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Установка атрибута"""
        if name == '_data':
            super().__setattr__(name, value)
        else:
            self._data[name] = DynamicConfig(value) if isinstance(value, dict) else value

    def __setitem__(self, name: str, value: Any) -> None:
        """Установка элемента как в словаре"""
        self._data[name] = DynamicConfig(value) if isinstance(value, dict) else value

    def __contains__(self, name: str) -> bool:
        """Проверка наличия атрибута"""
        return name in self._data

    def __repr__(self) -> str:
        return f"DynamicConfig({self._data})"

    def get(self, path: str, default: Any = None) -> Any:
        """Получает значение по пути (например: 'proxyApi.server.token')"""
        try:
            keys = path.split('.')
            value = self
            for key in keys:
                if hasattr(value, key):
                    value = getattr(value, key)
                elif isinstance(value, DynamicConfig) and key in value._data:
                    value = value._data[key]
                elif isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value
        except (AttributeError, KeyError):
            return default

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует конфиг в обычный словарь"""
        result = {}
        for key, value in self._data.items():
            if isinstance(value, DynamicConfig):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [item.to_dict() if isinstance(item, DynamicConfig) else item for item in value]
            else:
                result[key] = value
        return result

    def to_dict_masked(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Конвертирует конфиг в словарь с маскировкой чувствительных данных"""
        result = {}
        for key, value in self._data.items():
            if isinstance(value, DynamicConfig):
                result[key] = value.to_dict_masked(mask_sensitive)
            elif isinstance(value, list):
                result[key] = [item.to_dict_masked(mask_sensitive) if isinstance(item, DynamicConfig) else item for item
                               in value]
            else:
                if mask_sensitive and any(sensitive in key.lower() for sensitive in ['pass', 'token', 'key', 'secret']):
                    str_value = str(value)
                    if len(str_value) > 4:
                        value = f"{'*' * (len(str_value) - 4)}{str_value[-4:]}"
                    else:
                        value = "****"
                result[key] = value
        return result


class DatabaseConfig(DynamicConfig):
    """Конфигурация базы данных"""

    def __init__(self, data: Dict[str, Any] = None):
        data = data or {}
        defaults = {
            'host': "localhost",
            'port': 5432,
            'database': "app",
            'user': "postgres",
            'password': "",
            'db_type': "postgresql",
            'driver': ""
        }
        # Объединяем переданные данные с значениями по умолчанию
        merged_data = {**defaults, **data}
        super().__init__(merged_data)

    def detect_db_type(self) -> str:
        """Автоматически определяет тип базы данных на основе параметров"""
        # Если тип уже явно указан, используем его
        db_type = self._data.get('db_type', '')
        if db_type and db_type != "auto":
            return db_type

        # Определяем по характерным признакам
        database = self._data.get('database', '')
        host = self._data.get('host', '').lower()
        port = self._data.get('port', 0)

        if database and (database.endswith('.db') or database.endswith('.sqlite')):
            return "sqlite"
        elif port == 1433 or "mssql" in host or "sqlserver" in host:
            return "mssql"
        elif port == 3306 or "mysql" in host:
            return "mysql"
        elif port == 5432 or "postgres" in host:
            return "postgresql"
        else:
            # По умолчанию считаем что это PostgreSQL
            return "postgresql"

    def set_db_type(self, db_type: str):
        """Устанавливает тип базы данных вручную"""
        supported_types = ["postgresql", "mysql", "mssql", "sqlite", "oracle"]
        if db_type.lower() not in supported_types:
            raise ValueError(f"Unsupported database type: {db_type}. Supported types: {supported_types}")
        self._data['db_type'] = db_type.lower()

    def get_connection_string(self, masked: bool = False) -> str:
        """Возвращает строку подключения с экранированием спецсимволов"""
        # Определяем тип базы данных если не указан явно
        db_type = self.detect_db_type()

        host = self._data.get('host', 'localhost')
        port = self._data.get('port', 5432)
        database = self._data.get('database', 'app')
        user = self._data.get('user', 'postgres')
        password = self._data.get('password', '')
        driver = self._data.get('driver', '')

        if masked:
            if db_type == "sqlite":
                return f"sqlite:///{database}"
            else:
                return f"{db_type}://{user}:****@{host}:{port}/{database}"

        # Формируем connection string в зависимости от типа БД
        if db_type == "sqlite":
            # SQLite не требует аутентификации
            return f"sqlite:///{database}"

        elif db_type == "mysql":
            # Экранируем параметры для MySQL
            safe_user = quote_plus(user)
            safe_password = quote_plus(password)
            safe_host = quote_plus(host)
            safe_database = quote_plus(database)

            # Добавляем драйвер если указан
            driver_part = f"+{driver}" if driver else ""
            return f"mysql{driver_part}://{safe_user}:{safe_password}@{safe_host}:{port}/{safe_database}"

        elif db_type == "mssql":
            # Экранируем параметры для MSSQL
            safe_user = quote_plus(user)
            safe_password = quote_plus(password)
            safe_host = quote_plus(host)
            safe_database = quote_plus(database)

            # Добавляем драйвер если указан
            driver_part = f"+{driver}" if driver else ""
            return f"mssql{driver_part}://{safe_user}:{safe_password}@{safe_host}:{port}/{safe_database}"

        elif db_type == "postgresql":
            # Экранируем параметры для PostgreSQL
            safe_user = quote_plus(user)
            safe_password = quote_plus(password)
            safe_host = quote_plus(host)
            safe_database = quote_plus(database)

            # Добавляем драйвер если указан
            driver_part = f"+{driver}" if driver else ""
            return f"postgresql{driver_part}://{safe_user}:{safe_password}@{safe_host}:{port}/{safe_database}"

        else:
            # Для других типов БД используем общий формат
            safe_user = quote_plus(user)
            safe_password = quote_plus(password)
            return f"{db_type}://{safe_user}:{safe_password}@{host}:{port}/{database}"


class ConfigManager:
    """Менеджер конфигурации с поддержкой YAML и env переменных"""

    def __init__(self):
        self.config = DynamicConfig()
        self._loaded = False

    def load_from_yaml(self, filepath: str) -> DynamicConfig:
        """Загружает конфигурацию из YAML файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f) or {}

            self._load_dict_config(yaml_data)
            self._loaded = True
            logger.info(f"Configuration loaded from {filepath}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load YAML config: {e}")
            raise

    def load_from_dict(self, config_dict: Dict[str, Any]) -> DynamicConfig:
        """Загружает конфигурацию из словаря"""
        try:
            self._load_dict_config(config_dict)
            self._loaded = True
            logger.info("Configuration loaded from dict")
            return self.config
        except Exception as e:
            logger.error(f"Failed to load config from dict: {e}")
            raise

    def _load_dict_config(self, config_dict: Dict[str, Any]):
        """Загружает конфигурацию из словаря в объект Config"""
        # Преобразуем все вложенные словари в DynamicConfig
        processed_data = {}
        for key, value in config_dict.items():
            if key == 'databases' and isinstance(value, dict):
                # Особый случай для баз данных - создаем DatabaseConfig
                processed_data[key] = {
                    db_name: DatabaseConfig(db_config) for db_name, db_config in value.items()
                }
            elif isinstance(value, dict):
                processed_data[key] = DynamicConfig(value)
            elif isinstance(value, list):
                processed_data[key] = [
                    DatabaseConfig(item) if isinstance(item, dict) and any(
                        db_key in item for db_key in ['host', 'port', 'database', 'user', 'password']) else
                    DynamicConfig(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                processed_data[key] = value

        self.config = DynamicConfig(processed_data)

        # Apply environment variables override
        self._apply_env_overrides()

    def _apply_env_overrides(self):
        """Применяет переопределения из переменных окружения"""
        # Database overrides
        if os.getenv('DB_HOST') and hasattr(self.config, 'database'):
            self.config.database.host = os.getenv('DB_HOST')
        if os.getenv('DB_PORT') and hasattr(self.config, 'database'):
            self.config.database.port = int(os.getenv('DB_PORT'))
        if os.getenv('DB_USER') and hasattr(self.config, 'database'):
            self.config.database.user = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD') and hasattr(self.config, 'database'):
            self.config.database.password = os.getenv('DB_PASSWORD')
        if os.getenv('DB_NAME') and hasattr(self.config, 'database'):
            self.config.database.database = os.getenv('DB_NAME')
        if os.getenv('DB_TYPE') and hasattr(self.config, 'database'):
            self.config.database.db_type = os.getenv('DB_TYPE')
        if os.getenv('DB_DRIVER') and hasattr(self.config, 'database'):
            self.config.database.driver = os.getenv('DB_DRIVER')

        # Logger overrides
        if os.getenv('LOG_LEVEL') and hasattr(self.config, 'application') and hasattr(self.config.application,
                                                                                      'logger'):
            self.config.application.logger.level = os.getenv('LOG_LEVEL')

        # Server overrides
        if os.getenv('SERVER_URL') and hasattr(self.config, 'server'):
            self.config.server.url = os.getenv('SERVER_URL')

        # Proxy API overrides
        if os.getenv('PROXY_API_URL') and hasattr(self.config, 'proxyApi') and hasattr(self.config.proxyApi, 'server'):
            self.config.proxyApi.server.url = os.getenv('PROXY_API_URL')
        if os.getenv('PROXY_API_TOKEN') and hasattr(self.config, 'proxyApi') and hasattr(self.config.proxyApi,
                                                                                         'server'):
            self.config.proxyApi.server.token = os.getenv('PROXY_API_TOKEN')

    def get(self, path: str, default: Any = None) -> Any:
        """Получает значение по пути (например: 'proxyApi.server.token')"""
        return self.config.get(path, default)

    def to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Возвращает конфигурацию как словарь"""
        if mask_sensitive:
            return self.config.to_dict_masked(mask_sensitive)
        return self.config.to_dict()

    def log_config(self):
        """Логирует загруженную конфигурацию"""
        if not self._loaded:
            logger.warning("Config not loaded yet")
            return

        config_dict = self.to_dict(mask_sensitive=True)
        logger.info("🔧 Loaded configuration:")

        def log_section(data: Dict[str, Any], indent: int = 0):
            """Рекурсивно логирует секции конфигурации"""
            prefix = "  " * indent
            for key, value in data.items():
                if isinstance(value, dict):
                    logger.info(f"{prefix}{key}:")
                    log_section(value, indent + 1)
                elif isinstance(value, list):
                    logger.info(f"{prefix}{key}: {value}")
                else:
                    logger.info(f"{prefix}{key}: {value}")

        log_section(config_dict)


# Создание глобального экземпляра
config_manager = ConfigManager()