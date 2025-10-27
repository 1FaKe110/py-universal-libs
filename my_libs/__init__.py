# my_libs/__init__.py (ФИНАЛЬНЫЙ)
from __future__ import annotations

# Re-export основных модулей
from .api_client import (
    APIClient, APIResponse, create_client, api_manager,
    get, post, async_get, mock_mode, rate_limited,
    create_api_client, load_test, RetryPolicy, CircuitBreaker, RateLimiter
)
from .config import config_manager, Config, DatabaseConfig
from .database import db_manager, Database, QueryResult
from .http_client import HttpManager, HttpClient
from .kafka_client import KafkaManager, KafkaProducerWrapper, KafkaConsumerWrapper
from .logger import AppLogger, LoggerSetup, log_setup, app_logger
from .utils import data_utils, validation_utils, format_utils

__version__ = "0.1.1"
__author__ = "IFAKE110"
__email__ = "gabko2016@gmail.com"

__all__ = [
    # API Client
    'APIClient', 'APIResponse', 'create_client', 'api_manager',
    'get', 'post', 'async_get', 'mock_mode', 'rate_limited',
    'create_api_client', 'load_test', 'RetryPolicy', 'CircuitBreaker', 'RateLimiter',

    # Config
    'config_manager', 'Config', 'DatabaseConfig',

    # Database
    'db_manager', 'Database', 'QueryResult',

    # HTTP
    'HttpManager', 'HttpClient',

    # Kafka
    'KafkaManager', 'KafkaProducerWrapper', 'KafkaConsumerWrapper',

    # Logger
    'AppLogger', 'LoggerSetup', 'log_setup', 'app_logger',

    # Utils
    'data_utils', 'validation_utils', 'format_utils',
]