from __future__ import annotations
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional
from loguru import logger
import time


class HttpClient:
    """HTTP клиент с retry логикой и подробным логированием"""

    def __init__(
            self,
            base_url: str = "",
            timeout: int = 30,
            max_retries: int = 3,
            backoff_factor: float = 1.0
    ):
        self.session = requests.Session()
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # Настройка retry стратегии
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Убираем стандартные логи requests
        import logging
        logging.getLogger("urllib3").setLevel(logging.WARNING)

        self.stats = {"success": 0, "errors": 0, "total_time": 0.0}

    def request(
            self,
            method: str,
            endpoint: str,
            **kwargs
    ) -> Optional[requests.Response]:
        """Выполняет HTTP запрос с подробным логированием"""
        if self.base_url:
            if endpoint:
                # Убираем лишние слеши
                url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            else:
                url = self.base_url.rstrip('/')
        else:
            url = endpoint

        start_time = time.time()
        try:
            logger.info(f"🚀 HTTP {method.upper()} запрос: {url}")

            if kwargs.get('params'):
                logger.debug(f"📋 Параметры запроса: {kwargs['params']}")
            if kwargs.get('headers'):
                logger.debug(
                    f"📨 Заголовки: {{k: v for k, v in kwargs['headers'].items() if k.lower() not in ['authorization', 'cookie']}}")

            response = self.session.request(
                method=method.upper(),
                url=url,
                timeout=self.timeout,
                **kwargs
            )

            duration = time.time() - start_time
            self.stats["total_time"] += duration
            self.stats["success"] += 1

            # Детальное логирование ответа
            logger.info(f"✅ HTTP {method.upper()} {response.status_code} - {duration:.3f}s - {url}")

            if response.status_code >= 400:
                logger.warning(f"⚠️  Ответ с ошибкой: {response.status_code}")
                if len(response.text) < 1000:  # Логируем короткие ответы
                    logger.debug(f"📄 Тело ответа: {response.text}")

            return response

        except requests.exceptions.ConnectionError as e:
            duration = time.time() - start_time
            self.stats["errors"] += 1
            logger.error(f"🔌 Ошибка подключения: {e}")
            return None

        except requests.exceptions.Timeout as e:
            duration = time.time() - start_time
            self.stats["errors"] += 1
            logger.error(f"⏰ Таймаут запроса: {e}")
            return None

        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            self.stats["errors"] += 1
            logger.error(f"❌ Ошибка HTTP запроса: {e}")
            return None

    def get(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        return self.request("DELETE", endpoint, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику запросов"""
        total = self.stats["success"] + self.stats["errors"]
        avg_time = self.stats["total_time"] / max(self.stats["success"], 1)

        return {
            **self.stats,
            "total_requests": total,
            "success_rate": (self.stats["success"] / total * 100) if total > 0 else 0,
            "average_time_sec": round(avg_time, 3)
        }


class HttpManager:
    """Менеджер для работы с HTTP клиентами"""

    def __init__(self):
        self.clients = {}

    def get_client(self, base_url: str = "", **kwargs) -> HttpClient:
        """Возвращает HTTP клиент для базового URL"""
        key = base_url or "default"
        if key not in self.clients:
            self.clients[key] = HttpClient(base_url, **kwargs)
            logger.info(f"Создан HTTP клиент для: {base_url}")
        return self.clients[key]