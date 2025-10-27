# [file name]: __init__.py
from __future__ import annotations
import asyncio
import time
import random
import json
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager, contextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from unittest.mock import Mock
import aiohttp
import requests
from loguru import logger

try:
    from jsonschema import validate, ValidationError
except ImportError:
    validate = None
    ValidationError = Exception


@dataclass
class APIResponse:
    """Унифицированный ответ API"""
    status: int
    data: Any
    headers: Dict[str, str]
    elapsed: float
    url: str

    @property
    def success(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> Any:
        return self.data

    def raise_for_status(self):
        if not self.success:
            raise Exception(f"HTTP {self.status} for {self.url}")


class RetryPolicy:
    """Политика повторных попыток"""

    def __init__(
            self,
            max_retries: int = 3,
            backoff_factor: float = 1.0,
            retry_on: List[int] = None
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on or [429, 500, 502, 503, 504]

    def should_retry(self, status: int, attempt: int) -> bool:
        """Определяет, нужно ли повторять запрос"""
        return attempt < self.max_retries and status in self.retry_on

    def get_delay(self, attempt: int) -> float:
        """Возвращает задержку перед повторной попыткой"""
        return self.backoff_factor * (2 ** attempt)


class CircuitBreaker:
    """Circuit Breaker для защиты от сбоев"""

    def __init__(
            self,
            failure_threshold: int = 5,
            recovery_timeout: int = 60,
            expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0

    def can_execute(self) -> bool:
        """Проверяет, можно ли выполнять запрос"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def on_success(self):
        """Обработка успешного запроса"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.failures = 0

    def on_failure(self):
        """Обработка неудачного запроса"""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.failures >= self.failure_threshold:
            self.state = "OPEN"


class RateLimiter:
    """Rate limiting с разными алгоритмами"""

    def __init__(self, requests_per_second: int = 10, algorithm: str = "token_bucket"):
        self.rps = requests_per_second
        self.algorithm = algorithm
        self.tokens = requests_per_second
        self.last_refill = time.time()
        self.requests_history: List[float] = []

    def acquire(self) -> bool:
        """Проверяет можно ли выполнить запрос"""
        if self.algorithm == "token_bucket":
            return self._token_bucket_acquire()
        elif self.algorithm == "fixed_window":
            return self._fixed_window_acquire()
        else:
            return True

    def _token_bucket_acquire(self) -> bool:
        """Token bucket алгоритм"""
        now = time.time()
        time_passed = now - self.last_refill
        new_tokens = time_passed * self.rps

        self.tokens = min(self.rps, self.tokens + new_tokens)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def _fixed_window_acquire(self) -> bool:
        """Fixed window алгоритм"""
        now = time.time()
        window_start = now // 1  # Текущая секунда

        # Очищаем старые запросы
        self.requests_history = [t for t in self.requests_history if t >= window_start]

        if len(self.requests_history) < self.rps:
            self.requests_history.append(now)
            return True
        return False


class CacheManager:
    """Кеширование ответов"""

    def __init__(self, ttl: int = 300):  # 5 минут по умолчанию
        self.ttl = ttl
        self.cache: Dict[str, Dict] = {}

    def get_key(self, method: str, endpoint: str, params: Dict) -> str:
        """Генерирует ключ для кеша"""
        param_str = json.dumps(params, sort_keys=True) if params else ""
        return f"{method.upper()}_{endpoint}_{param_str}"

    def get(self, key: str) -> Optional[APIResponse]:
        """Получает данные из кеша"""
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached['timestamp'] < self.ttl:
                logger.debug(f"📦 Используется кешированный ответ для {key}")
                return cached['response']
            else:
                del self.cache[key]  # Удаляем просроченный кеш
        return None

    def set(self, key: str, response: APIResponse):
        """Сохраняет данные в кеш"""
        self.cache[key] = {
            'response': response,
            'timestamp': time.time()
        }


class ResponseValidator:
    """Валидация ответов по JSON Schema"""

    def __init__(self):
        self.schemas: Dict[str, Dict] = {}

    def add_schema(self, name: str, schema: Dict):
        """Добавляет схему для валидации"""
        self.schemas[name] = schema
        logger.debug(f"✅ Добавлена схема валидации: {name}")

    def validate_response(self, response: APIResponse, schema_name: str) -> bool:
        """Валидирует ответ по схеме"""
        if schema_name not in self.schemas:
            logger.warning(f"Схема '{schema_name}' не найдена")
            return False

        if validate is None:
            logger.warning("jsonschema не установлен, валидация недоступна")
            return False

        try:
            if isinstance(response.data, dict):
                validate(instance=response.data, schema=self.schemas[schema_name])
                logger.debug(f"✅ Ответ прошел валидацию по схеме '{schema_name}'")
                return True
            else:
                logger.warning("Ответ не является JSON объектом для валидации")
                return False
        except ValidationError as e:
            logger.error(f"❌ Ошибка валидации: {e}")
            return False


class MockManager:
    """Менеджер моков для тестирования"""

    def __init__(self):
        self.mocks: Dict[str, Mock] = {}
        self.enabled = False

    def add_mock(
            self,
            endpoint: str,
            method: str = "GET",
            response_data: Any = None,
            status: int = 200,
            headers: Dict = None
    ):
        """Добавляет мок для endpoint'а"""
        mock_key = f"{method.upper()}_{endpoint}"

        mock_response = Mock()
        mock_response.status = status
        mock_response.data = response_data or {"message": "Mock response"}
        mock_response.headers = headers or {}
        mock_response.elapsed = 0.1
        mock_response.success = 200 <= status < 300

        self.mocks[mock_key] = mock_response
        logger.debug(f"✅ Добавлен мок для {mock_key}")

    def enable_mocks(self):
        """Включает режим моков"""
        self.enabled = True
        logger.info("🔶 Режим моков ВКЛЮЧЕН")

    def disable_mocks(self):
        """Выключает режим моков"""
        self.enabled = False
        logger.info("🔷 Режим моков ВЫКЛЮЧЕН")

    def get_mock_response(self, method: str, endpoint: str) -> Optional[APIResponse]:
        """Возвращает мок-ответ если есть"""
        if not self.enabled:
            return None

        mock_key = f"{method.upper()}_{endpoint}"
        mock = self.mocks.get(mock_key)

        if mock:
            logger.debug(f"🎭 Используется мок для {mock_key}")
            return APIResponse(
                status=mock.status,
                data=mock.data,
                headers=mock.headers,
                elapsed=mock.elapsed,
                url=f"mock://{endpoint}"
            )

        return None


class MetricsCollector:
    """Сбор метрик производительности"""

    def __init__(self):
        self.metrics: Dict[str, List] = {
            'response_times': [],
            'status_codes': [],
            'errors': [],
            'throughput': []
        }
        self.start_time = time.time()

    def record_request(self, response: APIResponse):
        """Записывает метрики запроса"""
        self.metrics['response_times'].append(response.elapsed)
        self.metrics['status_codes'].append(response.status)

        if not response.success:
            self.metrics['errors'].append({
                'status': response.status,
                'url': response.url,
                'timestamp': time.time()
            })

    def get_summary(self) -> Dict:
        """Возвращает сводку метрик"""
        total_requests = len(self.metrics['response_times'])
        total_time = time.time() - self.start_time

        successful_requests = len([s for s in self.metrics['status_codes'] if 200 <= s < 300])

        return {
            'total_requests': total_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'avg_response_time': sum(self.metrics['response_times']) / total_requests if total_requests > 0 else 0,
            'requests_per_second': total_requests / total_time if total_time > 0 else 0,
            'error_count': len(self.metrics['errors']),
            'status_distribution': {
                code: self.metrics['status_codes'].count(code)
                for code in set(self.metrics['status_codes'])
            }
        }

    def print_metrics(self):
        """Выводит красивые метрики"""
        summary = self.get_summary()
        logger.info("📈 Метрики производительности:")
        logger.info(f"   Всего запросов: {summary['total_requests']}")
        logger.info(f"   Успешных: {summary['total_requests'] - summary['error_count']}")
        logger.info(f"   Ошибок: {summary['error_count']}")
        logger.info(f"   Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"   Среднее время: {summary['avg_response_time']:.3f}сек")
        logger.info(f"   RPS: {summary['requests_per_second']:.1f}")


class LoadTestResult:
    """Результаты нагрузочного тестирования"""

    def __init__(self, results: List[Dict], duration: int, total_requests: int, errors: int):
        self.results = results
        self.duration = duration
        self.total_requests = total_requests
        self.errors = errors

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.total_requests - self.errors) / self.total_requests * 100

    @property
    def avg_response_time(self) -> float:
        if not self.results:
            return 0.0
        successful_times = [r['elapsed'] for r in self.results if r.get('success')]
        if not successful_times:
            return 0.0
        return sum(successful_times) / len(successful_times)

    def print_summary(self):
        """Выводит красивый отчет"""
        logger.info("📊 Результаты нагрузочного теста:")
        logger.info(f"   Всего запросов: {self.total_requests}")
        logger.info(f"   Длительность: {self.duration}сек")
        logger.info(f"   Успешных: {self.total_requests - self.errors}")
        logger.info(f"   Ошибок: {self.errors}")
        logger.info(f"   Success Rate: {self.success_rate:.1f}%")
        logger.info(f"   Среднее время ответа: {self.avg_response_time:.3f}сек")
        logger.info(f"   RPS: {self.total_requests / self.duration:.1f}")


class LoadTest:
    """Инструмент нагрузочного тестирования"""

    def __init__(self, client: APIClient):
        self.client = client
        self.results: List[Dict] = []

    def run(
            self,
            endpoint: str,
            method: str = "GET",
            rps: int = 10,
            duration: int = 30,
            **kwargs
    ) -> LoadTestResult:
        """Запускает нагрузочный тест"""
        logger.info(f"🧪 Нагрузочный тест: {method} {endpoint}, {rps} RPS, {duration}сек")

        start_time = time.time()
        request_count = 0
        errors = 0

        while time.time() - start_time < duration:
            batch_start = time.time()

            # Создаем batch запросов для достижения целевого RPS
            futures = []
            with ThreadPoolExecutor(max_workers=rps) as executor:
                for _ in range(rps):
                    future = executor.submit(
                        self.client.request, method, endpoint, **kwargs
                    )
                    futures.append(future)

                # Ждем завершения batch
                for future in futures:
                    try:
                        response = future.result(timeout=self.client.timeout)
                        self.results.append({
                            'status': response.status,
                            'elapsed': response.elapsed,
                            'success': response.success,
                            'timestamp': time.time()
                        })
                        if not response.success:
                            errors += 1
                    except Exception as e:
                        errors += 1
                        self.results.append({
                            'status': 0,
                            'elapsed': 0,
                            'success': False,
                            'error': str(e),
                            'timestamp': time.time()
                        })
                    request_count += 1

            # Регулируем RPS
            batch_time = time.time() - batch_start
            if batch_time < 1.0:
                time.sleep(1.0 - batch_time)

        return LoadTestResult(self.results, duration, request_count, errors)


class APIClient:
    """Универсальный API клиент с полным набором фич"""

    def __init__(
            self,
            base_url: str = "",
            timeout: int = 30,
            default_headers: Dict[str, str] = None,
            session: requests.Session = None,
            retry_policy: RetryPolicy = None,
            circuit_breaker: CircuitBreaker = None,
            rate_limiter: RateLimiter = None,
            enable_cache: bool = False,
            enable_metrics: bool = False,
            enable_validation: bool = False
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.default_headers = default_headers or {}
        self._session = session or requests.Session()
        self._async_session: Optional[aiohttp.ClientSession] = None

        # Все фичи
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.rate_limiter = rate_limiter
        self.mock_manager = MockManager()
        self.validator = ResponseValidator() if enable_validation else None
        self.cache = CacheManager() if enable_cache else None
        self.metrics = MetricsCollector() if enable_metrics else None
        self.load_tester = LoadTest(self)

        self._setup_session()

    def _setup_session(self):
        """Настраивает HTTP сессию"""
        self._session.headers.update(self.default_headers)

    def _build_url(self, endpoint: str) -> str:
        """Строит полный URL"""
        if self.base_url:
            return f"{self.base_url}/{endpoint.lstrip('/')}"
        return endpoint

    def _process_response(self, response: requests.Response, elapsed: float) -> APIResponse:
        """Обрабатывает ответ в унифицированный формат"""
        try:
            data = response.json()
        except:
            data = response.text

        return APIResponse(
            status=response.status_code,
            data=data,
            headers=dict(response.headers),
            elapsed=elapsed,
            url=response.url
        )

    def request(
            self,
            method: str,
            endpoint: str,
            retry: bool = True,
            use_cache: bool = False,
            validate_schema: str = None,
            **kwargs
    ) -> APIResponse:
        """Базовый метод запроса со всеми фичами"""

        # 1. Проверяем моки
        mock_response = self.mock_manager.get_mock_response(method, endpoint)
        if mock_response:
            return mock_response

        # 2. Проверяем circuit breaker
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is OPEN")

        # 3. Проверяем rate limiting
        if self.rate_limiter and not self.rate_limiter.acquire():
            # Ждем пока не появится возможность
            while not self.rate_limiter.acquire():
                time.sleep(0.1)

        # 4. Проверяем кеш
        cache_key = None
        if use_cache and self.cache and method.upper() == "GET":
            cache_key = self.cache.get_key(method, endpoint, kwargs.get('params'))
            cached_response = self.cache.get(cache_key)
            if cached_response:
                return cached_response

        url = self._build_url(endpoint)
        attempt = 0

        while True:
            attempt += 1
            start_time = time.time()

            logger.debug(f"🚀 {method.upper()} {url} (попытка {attempt})")

            try:
                response = self._session.request(
                    method=method.upper(),
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )

                elapsed = time.time() - start_time
                api_response = self._process_response(response, elapsed)

                # Собираем метрики
                if self.metrics:
                    self.metrics.record_request(api_response)

                logger.debug(f"✅ {response.status_code} - {elapsed:.3f}s")

                # Валидация схемы
                if validate_schema and self.validator:
                    self.validator.validate_response(api_response, validate_schema)

                # Сохраняем в кеш
                if cache_key and self.cache and api_response.success:
                    self.cache.set(cache_key, api_response)

                # Успешный запрос
                if api_response.success:
                    self.circuit_breaker.on_success()
                    return api_response

                # Неуспешный, но может быть нужно повторить
                if (retry and
                        self.retry_policy.should_retry(api_response.status, attempt)):
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(f"🔄 Повтор через {delay:.1f}сек (статус: {api_response.status})")
                    time.sleep(delay)
                    continue

                # Неуспешный и не повторяем
                self.circuit_breaker.on_failure()
                return api_response

            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")
                self.circuit_breaker.on_failure()

                if (retry and
                        attempt < self.retry_policy.max_retries and
                        isinstance(e, self.circuit_breaker.expected_exceptions)):
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(f"🔄 Повтор через {delay:.1f}сек (ошибка: {e})")
                    time.sleep(delay)
                    continue

                raise

    # Короткие методы как в requests
    def get(self, endpoint: str, **kwargs) -> APIResponse:
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> APIResponse:
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> APIResponse:
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> APIResponse:
        return self.request("DELETE", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> APIResponse:
        return self.request("PATCH", endpoint, **kwargs)

    # Нагрузочное тестирование
    def load_test(
            self,
            endpoint: str,
            method: str = "GET",
            rps: int = 10,
            duration: int = 30,
            **kwargs
    ) -> LoadTestResult:
        """Запускает нагрузочный тест одной строкой"""
        return self.load_tester.run(endpoint, method, rps, duration, **kwargs)

    # Batch операции
    def batch(
            self,
            requests_config: List[Dict[str, Any]],
            parallel: bool = True
    ) -> List[APIResponse]:
        """Выполняет несколько запросов"""

        def make_request(config: Dict) -> APIResponse:
            method = config.get('method', 'GET')
            endpoint = config['endpoint']
            request_kwargs = {k: v for k, v in config.items()
                              if k not in ['method', 'endpoint']}
            return self.request(method, endpoint, **request_kwargs)

        if parallel:
            with ThreadPoolExecutor() as executor:
                return list(executor.map(make_request, requests_config))
        else:
            return [make_request(config) for config in requests_config]

    # Асинхронные методы
    async def async_request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        """Асинхронный запрос"""
        if not self._async_session:
            self._async_session = aiohttp.ClientSession(headers=self.default_headers)

        url = self._build_url(endpoint)
        start_time = time.time()

        logger.debug(f"🚀 [ASYNC] {method.upper()} {url}")

        async with self._async_session.request(
                method=method.upper(),
                url=url,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                **kwargs
        ) as response:
            elapsed = time.time() - start_time

            try:
                data = await response.json()
            except:
                data = await response.text()

            logger.debug(f"✅ [ASYNC] {response.status} - {elapsed:.3f}s")

            return APIResponse(
                status=response.status,
                data=data,
                headers=dict(response.headers),
                elapsed=elapsed,
                url=str(response.url)
            )

    # Асинхронные короткие методы
    async def async_get(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.async_request("GET", endpoint, **kwargs)

    async def async_post(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.async_request("POST", endpoint, **kwargs)

    async def async_put(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.async_request("PUT", endpoint, **kwargs)

    async def async_delete(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.async_request("DELETE", endpoint, **kwargs)

    async def async_patch(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.async_request("PATCH", endpoint, **kwargs)

    # Новые методы для управления фичами
    def enable_mocks(self):
        """Включает моки"""
        self.mock_manager.enable_mocks()

    def disable_mocks(self):
        """Выключает моки"""
        self.mock_manager.disable_mocks()

    def add_mock(self, endpoint: str, **kwargs):
        """Добавляет мок"""
        self.mock_manager.add_mock(endpoint, **kwargs)

    def add_schema(self, name: str, schema: Dict):
        """Добавляет схему валидации"""
        if self.validator:
            self.validator.add_schema(name, schema)
        else:
            logger.warning("Валидация отключена при создании клиента")

    def get_metrics(self) -> Dict:
        """Возвращает метрики"""
        return self.metrics.get_summary() if self.metrics else {}

    def print_metrics(self):
        """Выводит метрики"""
        if self.metrics:
            self.metrics.print_metrics()

    def close(self):
        """Закрывает сессии"""
        self._session.close()
        if self._async_session:
            asyncio.run(self._async_session.close())


class APIManager:
    """Менеджер для работы с несколькими API клиентами"""

    def __init__(self):
        self.clients: Dict[str, APIClient] = {}
        self._default_client: Optional[APIClient] = None

    def client(
            self,
            base_url: str = "",
            name: str = None,
            **kwargs
    ) -> APIClient:
        """Создает или возвращает существующий клиент"""
        client_name = name or base_url or "default"

        if client_name not in self.clients:
            self.clients[client_name] = APIClient(base_url, **kwargs)
            logger.info(f"Создан API клиент: {client_name}")

            if client_name == "default":
                self._default_client = self.clients[client_name]

        return self.clients[client_name]

    def get_client(self, name: str = None) -> APIClient:
        """Возвращает клиент по имени"""
        client_name = name or "default"
        if client_name not in self.clients:
            raise ValueError(f"API клиент '{client_name}' не найден")
        return self.clients[client_name]

    # Глобальные методы для быстрого доступа
    def get(self, endpoint: str, **kwargs) -> APIResponse:
        return self.get_client().get(endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> APIResponse:
        return self.get_client().post(endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> APIResponse:
        return self.get_client().put(endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> APIResponse:
        return self.get_client().delete(endpoint, **kwargs)

    async def async_get(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.get_client().async_get(endpoint, **kwargs)

    async def async_post(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.get_client().async_post(endpoint, **kwargs)

    async def async_put(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.get_client().async_put(endpoint, **kwargs)

    async def async_delete(self, endpoint: str, **kwargs) -> APIResponse:
        return await self.get_client().async_delete(endpoint, **kwargs)

    def close_all(self):
        """Закрывает все клиенты"""
        for name, client in self.clients.items():
            client.close()
            logger.debug(f"Закрыт API клиент: {name}")


# Фабрика для быстрого создания клиентов
def create_client(
        base_url: str = "",
        # Базовые настройки
        timeout: int = 30,
        default_headers: Dict = None,
        # Фичи
        enable_retry: bool = True,
        enable_circuit_breaker: bool = True,
        enable_rate_limiting: bool = False,
        rps_limit: int = 10,
        enable_cache: bool = False,
        enable_metrics: bool = False,
        enable_validation: bool = False,
        # Расширенные настройки
        retry_policy: Dict = None,
        circuit_breaker_config: Dict = None
) -> APIClient:
    """Фабрика для создания клиентов с предустановками"""

    # Настраиваем политики
    retry_policy_obj = RetryPolicy(**(retry_policy or {})) if enable_retry else None
    circuit_breaker_obj = CircuitBreaker(**(circuit_breaker_config or {})) if enable_circuit_breaker else None
    rate_limiter = RateLimiter(rps_limit) if enable_rate_limiting else None

    return APIClient(
        base_url=base_url,
        timeout=timeout,
        default_headers=default_headers,
        retry_policy=retry_policy_obj,
        circuit_breaker=circuit_breaker_obj,
        rate_limiter=rate_limiter,
        enable_cache=enable_cache,
        enable_metrics=enable_metrics,
        enable_validation=enable_validation
    )


# Декларативные клиенты
def create_api_client(
        base_url: str,
        endpoints: Dict[str, Dict],
        **client_kwargs
) -> APIClient:
    """Создает клиент с предопределенными endpoint'ами"""
    client = APIClient(base_url, **client_kwargs)

    # Динамически создаем методы для каждого endpoint'а
    for endpoint_name, config in endpoints.items():
        method = config.get('method', 'GET')
        path = config.get('path', '')

        def create_endpoint_method(meth=method, pth=path):
            def endpoint_method(self, **kwargs):
                return self.request(meth, pth, **kwargs)

            return endpoint_method

        # Добавляем метод к клиенту
        setattr(client, endpoint_name, create_endpoint_method())

    return client


# Глобальные утилиты
def load_test(
        endpoint: str,
        base_url: str = "",
        rps: int = 10,
        duration: int = 30,
        **kwargs
) -> LoadTestResult:
    """Быстрый нагрузочный тест одной функцией"""
    client = APIClient(base_url)
    try:
        return client.load_test(endpoint, rps=rps, duration=duration, **kwargs)
    finally:
        client.close()


# Контекстные менеджеры
@contextmanager
def mock_mode():
    """Контекстный менеджер для режима моков"""
    mock_client = create_client(enable_metrics=True)
    mock_client.enable_mocks()

    try:
        yield mock_client
    finally:
        mock_client.disable_mocks()
        mock_client.close()


@contextmanager
def rate_limited(rps: int = 10):
    """Контекстный менеджер для rate limiting"""
    client = create_client(enable_rate_limiting=True, rps_limit=rps)
    try:
        yield client
    finally:
        client.close()


@contextmanager
def api_session(base_url: str = "", **kwargs):
    """Контекстный менеджер для API сессии"""
    client = APIClient(base_url, **kwargs)
    try:
        yield client
    finally:
        client.close()


# Глобальный менеджер
api_manager = APIManager()

# Создание клиента по умолчанию
api = api_manager.client()


# Псевдонимы для быстрого доступа
def get(endpoint: str, **kwargs) -> APIResponse:
    return api.get(endpoint, **kwargs)


def post(endpoint: str, **kwargs) -> APIResponse:
    return api.post(endpoint, **kwargs)


def put(endpoint: str, **kwargs) -> APIResponse:
    return api.put(endpoint, **kwargs)


def delete(endpoint: str, **kwargs) -> APIResponse:
    return api.delete(endpoint, **kwargs)


async def async_get(endpoint: str, **kwargs) -> APIResponse:
    return await api.async_get(endpoint, **kwargs)


async def async_post(endpoint: str, **kwargs) -> APIResponse:
    return await api.async_post(endpoint, **kwargs)


async def async_put(endpoint: str, **kwargs) -> APIResponse:
    return await api.async_put(endpoint, **kwargs)


async def async_delete(endpoint: str, **kwargs) -> APIResponse:
    return await api.async_delete(endpoint, **kwargs)

