from __future__ import annotations

# Re-export из всех модулей
from .api import *
from .config import *
from .database import *
from .http import *
from .kafka import *
from .logger import *
from .utils import *

__version__ = "0.1.1"
__author__ = "IFAKE110"
__email__ = "gabko2016@gmail.com"

# Собираем все __all__ из подмодулей
__all__ = (
    api.__all__ +
    config.__all__ + 
    database.__all__ +
    http.__all__ +
    kafka.__all__ +
    logger.__all__ +
    utils.__all__
)