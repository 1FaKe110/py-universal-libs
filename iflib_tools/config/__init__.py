from __future__ import annotations

from .config import (
    config_manager, DynamicConfig, DatabaseConfig, ConfigManager
)

# Псевдонимы для обратной совместимости
Config = DynamicConfig
BaseConfig = DynamicConfig

__all__ = [
    'config_manager',
    'Config',           # Псевдоним для DynamicConfig
    'BaseConfig',       # Псевдоним для DynamicConfig
    'DynamicConfig',    # Основной класс
    'DatabaseConfig',
    'ConfigManager'
]