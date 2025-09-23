from __future__ import annotations
import os
from urllib.parse import quote_plus

import yaml
from typing import Any, Dict, List, Optional, Type, TypeVar
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

T = TypeVar('T')


class BaseConfig:
    """Базовый класс для конфигурации с поддержкой env переменных"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseConfig:
        """Создает конфиг из словаря"""
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Конвертирует конфиг в словарь (с маскировкой по умолчанию)"""
        result = {}
        for key in dir(self):
            if key.startswith('_') or key in ['from_dict', 'to_dict']:
                continue
            value = getattr(self, key)
            if not callable(value):
                if mask_sensitive and any(sensitive in key.lower() for sensitive in ['pass', 'token', 'key', 'secret']):
                    str_value = str(value)
                    if len(str_value) > 4:
                        value = f"{'*' * (len(str_value) - 4)}{str_value[-4:]}"
                    else:
                        value = "****"
                result[key] = value
        return result


class DatabaseConfig(BaseConfig):
    """Конфигурация базы данных"""

    def __init__(
            self,
            host: str = "localhost",
            port: int = 5432,
            database: str = "app",
            user: str = "postgres",
            password: str = ""
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def get_connection_string(self, masked: bool = False) -> str:
        """Возвращает строку подключения с экранированием спецсимволов"""
        if masked:
            return f"postgresql://{self.user}:****@{self.host}:{self.port}/{self.database}"

        # Экранируем ВСЕ специальные символы в каждом компоненте
        safe_user = quote_plus(self.user)
        safe_password = quote_plus(self.password)
        safe_host = quote_plus(self.host)  # На всякий случай
        safe_database = quote_plus(self.database)

        # Формируем connection string с экранированными значениями
        return f"postgresql://{safe_user}:{safe_password}@{self.host}:{self.port}/{safe_database}"

class ServerConfig(BaseConfig):
    """Конфигурация сервера"""

    def __init__(self, url: str = "", endpoint: str = "", headers: Dict[str, str] = None):
        self.url = url.rstrip('/')
        self.endpoint = endpoint
        self.headers = headers or {}


class LoggerConfig(BaseConfig):
    """Конфигурация логгера"""

    def __init__(self, level: str = "INFO", format: str = None, file: str = None):
        self.level = level
        self.format = format
        self.file = file


class ApplicationConfig(BaseConfig):
    """Конфигурация приложения"""

    def __init__(self, logger: LoggerConfig = None, name: str = "app", env: str = "development"):
        self.logger = logger or LoggerConfig()
        self.name = name
        self.env = env


class Config(BaseConfig):
    """Основной класс конфигурации"""

    def __init__(self):
        self.application = ApplicationConfig()
        self.server = ServerConfig()
        self.database = DatabaseConfig()

        # Динамические базы данных
        self._databases: Dict[str, DatabaseConfig] = {}

    def add_database(self, name: str, db_config: DatabaseConfig):
        """Добавляет дополнительную базу данных"""
        self._databases[name] = db_config

    def get_database(self, name: str) -> Optional[DatabaseConfig]:
        """Получает конфигурацию базы данных по имени"""
        if name == "default":
            return self.database
        return self._databases.get(name)

    def get_databases(self) -> List[str]:
        """Получает конфигурацию базы данных по имени"""
        return self._databases.keys()

    def list_databases(self) -> Dict[str, DatabaseConfig]:
        """Возвращает все базы данных"""
        databases = {"default": self.database}
        databases.update(self._databases)
        return databases


class ConfigManager:
    """Менеджер конфигурации с поддержкой YAML и env переменных"""

    def __init__(self):
        self.config = Config()
        self._loaded = False

    def load_from_yaml(self, filepath: str) -> Config:
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

    def load_from_dict(self, config_dict: Dict[str, Any]) -> Config:
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

        # Application config
        if 'application' in config_dict:
            app_data = config_dict['application']
            if 'logger' in app_data:
                self.config.application.logger = LoggerConfig(**app_data['logger'])
            if 'name' in app_data:
                self.config.application.name = app_data['name']
            if 'env' in app_data:
                self.config.application.env = app_data['env']

        # Server config
        if 'server' in config_dict:
            server_data = config_dict['server']
            self.config.server = ServerConfig(**server_data)

        # Main database config
        if 'database' in config_dict:
            db_data = config_dict['database']
            self.config.database = DatabaseConfig(**db_data)

        # Additional databases
        if 'databases' in config_dict:
            for db_name, db_config in config_dict['databases'].items():
                self.config.add_database(db_name, DatabaseConfig(**db_config))

        # Apply environment variables override
        self._apply_env_overrides()

    def _apply_env_overrides(self):
        """Применяет переопределения из переменных окружения"""

        # Database overrides
        if os.getenv('DB_HOST'):
            self.config.database.host = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            self.config.database.port = int(os.getenv('DB_PORT'))
        if os.getenv('DB_USER'):
            self.config.database.user = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            self.config.database.password = os.getenv('DB_PASSWORD')
        if os.getenv('DB_NAME'):
            self.config.database.database = os.getenv('DB_NAME')

        # Logger overrides
        if os.getenv('LOG_LEVEL'):
            self.config.application.logger.level = os.getenv('LOG_LEVEL')

        # Server overrides
        if os.getenv('SERVER_URL'):
            self.config.server.url = os.getenv('SERVER_URL')

    def get(self, path: str, default: Any = None) -> Any:
        """Получает значение по пути (например: 'database.host')"""
        try:
            keys = path.split('.')
            value = self.config
            for key in keys:
                value = getattr(value, key)
            return value
        except AttributeError:
            return default

    def to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Возвращает конфигурацию как словарь"""
        return self.config.to_dict(mask_sensitive)

    def log_config(self):
        """Логирует загруженную конфигурацию"""
        if not self._loaded:
            logger.warning("Config not loaded yet")
            return

        config_dict = self.to_dict(mask_sensitive=True)
        logger.info("🔧 Loaded configuration:")

        for section, values in config_dict.items():
            if section == 'application':
                logger.info(f"  📱 Application:")
                for key, value in values.items():
                    logger.info(f"     {key}: {value}")

            elif section == 'server':
                logger.info(f"  🌐 Server:")
                for key, value in values.items():
                    logger.info(f"     {key}: {value}")

            elif section == 'database':
                logger.info(f"  🗄️  Main Database:")
                for key, value in values.items():
                    logger.info(f"     {key}: {value}")

            elif section == '_databases':
                logger.info(f"  🗄️  Additional Databases:")
                for db_name, db_config in values.items():
                    logger.info(f"     {db_name}:")
                    for key, value in db_config.items():
                        logger.info(f"       {key}: {value}")


# Создание глобального экземпляра
config_manager = ConfigManager()

# # Пример YAML конфигурации
# DEFAULT_CONFIG_YAML = """
# application:
#   name: "My Application"
#   env: "development"
#   logger:
#     level: "INFO"
#     format: "simple"
#     file: "logs/app.log"
#
# server:
#   url: "https://api.example.com"
#   endpoint: "/api/v1"
#   headers:
#     accept: "application/json"
#     user-agent: "MyApp/1.0"
#
# database:
#   host: "localhost"
#   port: 5432
#   database: "myapp"
#   user: "postgres"
#   password: "password"
#
# databases:
#   analytics:
#     host: "analytics-db.example.com"
#     port: 5432
#     database: "analytics"
#     user: "analytics_user"
#     password: "analytics_password"
#   cache:
#     host: "cache-db.example.com"
#     port: 5432
#     database: "cache"
#     user: "cache_user"
#     password: "cache_password"
# """
# config_manager.load_from_yaml("config.yaml")
# config_manager.load_from_dict(config_dict)
#
# # 3. Использование
# from config import config_manager
#
# config = config_manager.config
#
# print(config.application.logger.level)  # DEBUG
# print(config.server.url)  # https://documents-circulation-api.example.com
# print(config.database.get_connection_string(masked=True))  # postgresql://egais-management-user:****@db-host:5432/transport
#
# # Работа с дополнительными базами
# analytics_db = config.get_database("analytics")
# if analytics_db:
#     print(analytics_db.get_connection_string(masked=True))
#
# # Логирование конфигурации
# config_manager.log_config()