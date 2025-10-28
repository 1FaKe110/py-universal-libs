# Универсальный API Клиент

Мощный и гибкий HTTP клиент для Python с поддержкой современных паттернов и инструментов для работы с API.

## Возможности

- ✅ **Синхронные и асинхронные запросы**
- 🔄 **Повторные попытки** с экспоненциальной backoff стратегией
- ⚡ **Circuit Breaker** для защиты от сбоев
- 🚦 **Rate Limiting** с разными алгоритмами
- 📦 **Кеширование** ответов
- 🎭 **Моки** для тестирования
- 📊 **Метрики** производительности
- 🧪 **Нагрузочное тестирование**
- 📋 **Валидация** по JSON Schema
- 🔧 **Batch операции**
- 📝 **Логирование** с loguru

## Установка

```bash
pip install requests aiohttp loguru jsonschema
```

# Быстрый старт
### Простое использование

```python
from api_client import get, post
```

### Простой GET запрос

```
response = get("https://api.example.com/users")
if response.success:
    print(response.json())
```

### POST запрос с данными
```python
response = post("https://api.example.com/users", json={"name": "John"})
```

# Создание клиента
```python
from api_client import create_client

# Клиент с базовыми настройками
client = create_client(
    base_url="https://api.example.com",
    timeout=30,
    enable_retry=True,
    enable_metrics=True
)

response = client.get("/users")
```

Расширенный клиент
```python
client = create_client(
    base_url="https://api.example.com",
    enable_retry=True,
    enable_circuit_breaker=True,
    enable_rate_limiting=True,
    rps_limit=10,
    enable_cache=True,
    enable_metrics=True,
    retry_policy={"max_retries": 5, "backoff_factor": 2.0}
)
```
Основные возможности
Повторные попытки
```python
# Автоматические повторы при 5xx ошибках
response = client.get("/unstable-endpoint", retry=True)
```

Circuit Breaker
```python
# Защита от частых сбоев
client = create_client(
    enable_circuit_breaker=True,
    circuit_breaker_config={
        "failure_threshold": 5,
        "recovery_timeout": 60
    }
)
```
Rate Limiting
```python
# Ограничение 10 запросов в секунду
client = create_client(
    enable_rate_limiting=True,
    rps_limit=10
)
```
Кеширование
```python
# Кеширование GET запросов
response = client.get("/stable-data", use_cache=True)
```
Валидация ответов
```python
# Добавление схемы валидации
schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"}
    },
    "required": ["id", "name"]
}

client.add_schema("user", schema)

# Валидация ответа
response = client.get("/user/1", validate_schema="user")
```

Моки для тестирования
```python
client.enable_mocks()
client.add_mock(
    "/users",
    method="GET",
    response_data=[{"id": 1, "name": "Test User"}],
    status=200
)

# Будет возвращен мок-ответ
response = client.get("/users")
```
Метрики
```python
client = create_client(enable_metrics=True)

# Выполнение запросов...
client.get("/endpoint1")
client.post("/endpoint2")

# Просмотр метрик
metrics = client.get_metrics()
client.print_metrics()
```
Нагрузочное тестирование
```python
result = client.load_test(
    endpoint="/api/data",
    method="GET",
    rps=50,
    duration=60
)

result.print_summary()
```
Batch запросы
```python
requests_config = [
    {"method": "GET", "endpoint": "/users/1"},
    {"method": "GET", "endpoint": "/users/2"},
    {"method": "POST", "endpoint": "/users", "json": {"name": "John"}}
]

responses = client.batch(requests_config, parallel=True)
```
Асинхронные запросы
```python
import asyncio

async def fetch_data():
    response = await client.async_get("/users")
    return response.json()

# Или используя глобальные функции
async def main():
    response = await async_get("https://api.example.com/users")
    print(response.json())
    
```
API Manager
Для работы с несколькими API:

```python
from api_client import api_manager

# Создание клиентов для разных сервисов
user_client = api_manager.client(
    base_url="https://api.users.com",
    name="users"
)

payment_client = api_manager.client(
    base_url="https://api.payments.com", 
    name="payments"
)

# Использование
users = user_client.get("/users")
payments = payment_client.get("/transactions")
```
Контекстные менеджеры
Режим моков
```python
from api_client import mock_mode

with mock_mode() as client:
    client.add_mock("/test", response_data={"mocked": True})
    response = client.get("/test")  # Возвращает мок-данные
```
Rate limiting
```python
from api_client import rate_limited

with rate_limited(rps=5) as client:
    # Все запросы ограничены 5 RPS
    for i in range(10):
        client.get(f"/item/{i}")
```

API сессия
```python
from api_client import api_session

with api_session("https://api.example.com") as client:
    response = client.get("/data")
    # Сессия автоматически закроется
```
Декораторы
Создание клиента с предопределенными endpoint'ами:

```python
from api_client import create_api_client

endpoints = {
    "get_user": {"method": "GET", "path": "/users/{id}"},
    "create_user": {"method": "POST", "path": "/users"},
    "update_user": {"method": "PUT", "path": "/users/{id}"}
}

client = create_api_client(
    base_url="https://api.example.com",
    endpoints=endpoints
)

# Использование
user = client.get_user(params={"id": 123})
new_user = client.create_user(json={"name": "John"})
```
Обработка ошибок
```python
try:
    response = client.get("/endpoint")
    response.raise_for_status()  # Выбрасывает исключение при ошибке
except Exception as e:
    print(f"Request failed: {e}")
```
Логирование
Клиент использует loguru для логирования. Уровень логирования можно настроить:

```python
import loguru
loguru.logger.remove()
loguru.logger.add(sys.stderr, level="INFO")
```
Производительность
Для максимальной производительности:

```python
client = create_client(
    enable_metrics=False,  # Отключить сбор метрик
    enable_validation=False,  # Отключить валидацию
    enable_cache=True,  # Включить кеширование
    retry_policy={"max_retries": 2}  # Уменьшить повторные попытки
)
```
Лицензия
MIT


## examples.py

```python
"""
Примеры использования API клиента
"""

import asyncio
import time
from api_client import (
    APIClient, create_client, api_manager, 
    get, post, async_get, mock_mode, rate_limited,
    create_api_client, load_test
)


def example_basic_usage():
    """Базовое использование"""
    print("=== Базовое использование ===")
    
    # Простые глобальные функции
    response = get("https://httpbin.org/json")
    if response.success:
        print(f"Status: {response.status}")
        print(f"Data: {response.json()}")
    print()


def example_client_creation():
    """Создание клиентов"""
    print("=== Создание клиентов ===")
    
    # Простой клиент
    client1 = APIClient(base_url="https://api.github.com")
    
    # Через фабрику с настройками
    client2 = create_client(
        base_url="https://api.github.com",
        timeout=30,
        enable_retry=True,
        enable_metrics=True,
        enable_cache=True
    )
    
    # Через менеджер
    client3 = api_manager.client(
        base_url="https://api.github.com",
        name="github"
    )
    
    print("Клиенты созданы успешно")
    print()


def example_retry_circuit_breaker():
    """Повторные попытки и Circuit Breaker"""
    print("=== Повторные попытки и Circuit Breaker ===")
    
    client = create_client(
        base_url="https://httpbin.org",
        enable_retry=True,
        enable_circuit_breaker=True,
        retry_policy={"max_retries": 3, "backoff_factor": 1.0},
        circuit_breaker_config={"failure_threshold": 3, "recovery_timeout": 30}
    )
    
    try:
        # Этот endpoint иногда возвращает 500 ошибку
        response = client.get("/status/500", retry=True)
        print(f"Final status: {response.status}")
    except Exception as e:
        print(f"Request failed: {e}")
    print()


def example_rate_limiting():
    """Rate limiting"""
    print("=== Rate Limiting ===")
    
    client = create_client(
        base_url="https://httpbin.org",
        enable_rate_limiting=True,
        rps_limit=2  # 2 запроса в секунду
    )
    
    start_time = time.time()
    for i in range(5):
        response = client.get(f"/delay/0.5")  # Запрос занимает 0.5 секунды
        print(f"Request {i+1}: {response.status} - {time.time() - start_time:.2f}s")
    
    print()


def example_caching():
    """Кеширование"""
    print("=== Кеширование ===")
    
    client = create_client(
        base_url="https://httpbin.org",
        enable_cache=True
    )
    
    # Первый запрос - выполняется
    start_time = time.time()
    response1 = client.get("/json", use_cache=True)
    time1 = time.time() - start_time
    
    # Второй запрос - из кеша (быстрее)
    start_time = time.time()
    response2 = client.get("/json", use_cache=True)
    time2 = time.time() - start_time
    
    print(f"First request: {time1:.3f}s")
    print(f"Second request: {time2:.3f}s")
    print(f"From cache: {time2 < time1}")
    print()


def example_mocking():
    """Моки для тестирования"""
    print("=== Моки ===")
    
    client = create_client(base_url="https://api.example.com")
    
    # Включаем моки и добавляем мок-данные
    client.enable_mocks()
    client.add_mock(
        "/users/1",
        method="GET",
        response_data={"id": 1, "name": "Mock User", "email": "mock@example.com"},
        status=200
    )
    
    # Запрос вернет мок-данные
    response = client.get("/users/1")
    print(f"Mock response: {response.json()}")
    
    client.disable_mocks()
    print()


def example_validation():
    """Валидация JSON Schema"""
    print("=== Валидация ===")
    
    client = create_client(
        base_url="https://httpbin.org",
        enable_validation=True
    )
    
    # Добавляем схему валидации
    user_schema = {
        "type": "object",
        "properties": {
            "slideshow": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                    "slides": {"type": "array"}
                },
                "required": ["title", "author", "slides"]
            }
        },
        "required": ["slideshow"]
    }
    
    client.add_schema("slideshow", user_schema)
    
    # Валидируем ответ
    response = client.get("/json", validate_schema="slideshow")
    print(f"Validation passed: {response.success}")
    print()


def example_metrics():
    """Сбор метрик"""
    print("=== Метрики ===")
    
    client = create_client(
        base_url="https://httpbin.org",
        enable_metrics=True
    )
    
    # Выполняем несколько запросов
    for i in range(5):
        client.get(f"/status/{200 if i % 2 == 0 else 404}")
    
    # Смотрим метрики
    metrics = client.get_metrics()
    print(f"Total requests: {metrics['total_requests']}")
    print(f"Success rate: {metrics['success_rate']:.1f}%")
    print(f"Average response time: {metrics['avg_response_time']:.3f}s")
    
    client.print_metrics()
    print()


def example_batch_requests():
    """Пакетные запросы"""
    print("=== Пакетные запросы ===")
    
    client = create_client(base_url="https://httpbin.org")
    
    requests_config = [
        {"method": "GET", "endpoint": "/get"},
        {"method": "GET", "endpoint": "/json"}, 
        {"method": "POST", "endpoint": "/post", "json": {"test": "data"}},
        {"method": "PUT", "endpoint": "/put", "json": {"update": "data"}}
    ]
    
    # Параллельное выполнение
    responses = client.batch(requests_config, parallel=True)
    
    for i, response in enumerate(responses):
        print(f"Request {i+1}: {response.status} - {response.elapsed:.3f}s")
    
    print()


def example_load_testing():
    """Нагрузочное тестирование"""
    print("=== Нагрузочное тестирование ===")
    
    client = create_client(base_url="https://httpbin.org")
    
    # Быстрый тест на 10 секунд
    result = client.load_test(
        endpoint="/delay/0.1",
        method="GET",
        rps=5,
        duration=5
    )
    
    result.print_summary()
    print()


async def example_async_requests():
    """Асинхронные запросы"""
    print("=== Асинхронные запросы ===")
    
    client = create_client(base_url="https://httpbin.org")
    
    # Несколько асинхронных запросов
    tasks = [
        client.async_get("/delay/1"),
        client.async_get("/delay/2"), 
        client.async_get("/json")
    ]
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, response in enumerate(responses):
        if isinstance(response, Exception):
            print(f"Request {i+1} failed: {response}")
        else:
            print(f"Request {i+1}: {response.status} - {response.elapsed:.3f}s")
    
    print()


def example_context_managers():
    """Контекстные менеджеры"""
    print("=== Контекстные менеджеры ===")
    
    # Режим моков
    with mock_mode() as mock_client:
        mock_client.add_mock("/test", response_data={"context": "mock"})
        response = mock_client.get("/test")
        print(f"Context mock: {response.json()}")
    
    # Rate limiting
    with rate_limited(rps=3) as limited_client:
        limited_client.base_url = "https://httpbin.org"
        start = time.time()
        for i in range(5):
            response = limited_client.get("/get")
            print(f"Rate limited {i+1}: {time.time() - start:.2f}s")
    
    print()


def example_declarative_client():
    """Декларативный клиент"""
    print("=== Декларативный клиент ===")
    
    endpoints = {
        "get_user": {"method": "GET", "path": "/users/{id}"},
        "create_user": {"method": "POST", "path": "/users"},
        "update_user": {"method": "PUT", "path": "/users/{id}"},
        "delete_user": {"method": "DELETE", "path": "/users/{id}"}
    }
    
    client = create_api_client(
        base_url="https://jsonplaceholder.typicode.com",
        endpoints=endpoints
    )
    
    # Использование предопределенных методов
    users = client.get_user(params={"id": 1})
    print(f"Get user: {users.status}")
    
    # Создание пользователя
    new_user = client.create_user(json={
        "name": "John Doe",
        "email": "john@example.com"
    })
    print(f"Create user: {new_user.status}")
    print()


def example_error_handling():
    """Обработка ошибок"""
    print("=== Обработка ошибок ===")
    
    client = create_client(base_url="https://httpbin.org")
    
    try:
        response = client.get("/status/404")
        
        # Проверка статуса
        if not response.success:
            print(f"Request failed with status: {response.status}")
        
        # Или выбросить исключение
        response.raise_for_status()
        
    except Exception as e:
        print(f"Error: {e}")
    
    print()


def example_api_manager():
    """Менеджер нескольких API"""
    print("=== Менеджер API ===")
    
    # Создаем клиенты для разных сервисов
    jsonplaceholder = api_manager.client(
        base_url="https://jsonplaceholder.typicode.com",
        name="jsonplaceholder"
    )
    
    httpbin = api_manager.client(
        base_url="https://httpbin.org", 
        name="httpbin"
    )
    
    # Используем разные клиенты
    users = jsonplaceholder.get("/users/1")
    http_info = httpbin.get("/get")
    
    print(f"JSONPlaceholder status: {users.status}")
    print(f"Httpbin status: {http_info.status}")
    
    # Закрываем все клиенты
    api_manager.close_all()
    print()


async def main():
    """Запуск всех примеров"""
    print("🚀 Запуск примеров API клиента\n")
    
    example_basic_usage()
    example_client_creation()
    example_retry_circuit_breaker()
    example_rate_limiting()
    example_caching()
    example_mocking()
    example_validation()
    example_metrics()
    example_batch_requests()
    example_load_testing()
    example_context_managers()
    example_declarative_client()
    example_error_handling()
    example_api_manager()
    
    # Асинхронные примеры
    await example_async_requests()
    
    print("✅ Все примеры завершены!")


if __name__ == "__main__":
    asyncio.run(main())
```