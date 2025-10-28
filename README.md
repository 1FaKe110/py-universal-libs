# Python Utilities Library (iflib-tools)

Полнофункциональная библиотека утилит для Python-разработки, предоставляющая готовые решения для работы с конфигурацией, базами данных, Kafka, HTTP-запросами, логированием и другими распространенными задачами.

## 📦 Установка

```bash
pip install iflib-tools
```

## 🏗️ Структура проекта

```
iflib_tools/
├── config/          # Управление конфигурацией
├── database/        # Универсальный обработчик БД
├── http/            # HTTP клиент с retry логикой
├── kafka/           # Producer/Consumer для Apache Kafka
├── logger/          # Продвинутая система логирования
└── utils/           # Вспомогательные утилиты
```

## 🚀 Быстрый старт

```python
from iflib_tools import config_manager, AppLogger, db_manager

# Загрузка конфигурации
config_manager.load_from_dict({
    'application': {
        'name': 'MyApp',
        'env': 'development'
    },
    'database': {
        'host': 'localhost',
        'port': 5432,
        'database': 'myapp',
        'user': 'postgres',
        'password': 'password'
    }
})

# Инициализация компонентов
logger = AppLogger(name=config_manager.config.application.name)
db = db_manager.add_database(
    name="main",
    connection_string=config_manager.config.database.get_connection_string(),
    set_default=True
)

logger.info("Приложение инициализировано")
```

## ⚙️ Модуль конфигурации (config)

### DynamicConfig - динамическая конфигурация

```python
from iflib_tools import DynamicConfig, DatabaseConfig

# Создание конфигурации
config = DynamicConfig({
    'app': {
        'name': 'MyApp',
        'version': '1.0.0'
    },
    'database': {
        'host': 'localhost',
        'port': 5432
    }
})

# Доступ к значениям
print(config.app.name)  # MyApp
print(config['app']['version'])  # 1.0.0

# Получение по пути
value = config.get('app.name')  # MyApp
value = config.get('non.existent.path', 'default')  # default
```

### DatabaseConfig - специализированная конфигурация БД

```python
# Автоматическое определение типа БД
db_config = DatabaseConfig({
    'host': 'localhost',
    'port': 5432,
    'database': 'myapp',
    'user': 'postgres',
    'password': 'secret'
})

# Ручное указание типа
db_config.set_db_type('postgresql')

# Генерация строки подключения
conn_string = db_config.get_connection_string()
# postgresql://postgres:secret@localhost:5432/myapp

conn_string_masked = db_config.get_connection_string(masked=True)
# postgresql://postgres:****@localhost:5432/myapp
```

### ConfigManager - централизованное управление

```python
from iflib_tools import config_manager

# Загрузка из YAML
config_manager.load_from_yaml('config.yaml')

# Загрузка из словаря
config_manager.load_from_dict({
    'application': {
        'name': 'TestApp',
        'logger': {'level': 'DEBUG'}
    },
    'databases': {
        'main': {
            'host': 'db.example.com',
            'port': 5432,
            'database': 'app',
            'user': 'user',
            'password': 'pass'
        },
        'analytics': {
            'host': 'analytics-db.example.com',
            'database': 'analytics',
            'user': 'analytics_user',
            'password': 'analytics_pass'
        }
    }
})

# Использование
app_name = config_manager.config.application.name
db_conn_string = config_manager.config.databases.main.get_connection_string()

# Получение значений по пути
log_level = config_manager.get('application.logger.level', 'INFO')
```

**Пример config.yaml:**
```yaml
application:
  name: "Production App"
  env: "production"
  logger:
    level: "INFO"
    format: "detailed"

server:
  url: "https://api.company.com"
  timeout: 30

databases:
  primary:
    host: "primary-db.company.com"
    port: 5432
    database: "app_primary"
    user: "app_user"
    password: "secure_password"
    db_type: "postgresql"

  replica:
    host: "replica-db.company.com"
    port: 5432
    database: "app_replica"
    user: "readonly_user"
    password: "readonly_pass"
    db_type: "postgresql"

kafka:
  bootstrap_servers: "kafka1:9092,kafka2:9092"
  topics:
    events: "app-events"
    metrics: "app-metrics"
```

## 📝 Модуль логирования (logger)

### LoggerSetup - настройка логгера

```python
from iflib_tools import LoggerSetup

# Базовая настройка
log_setup = LoggerSetup(level="DEBUG")

# Расширенная настройка
log_setup = LoggerSetup(
    level="INFO",
    enable_file_logging=True  # Включает запись в файлы
)

# Кастомный формат через наследование
class CustomLoggerSetup(LoggerSetup):
    def _console_format(self, record):
        return f"🪵 [{record['level']}] {record['message']}\n"
```

### AppLogger - структурированное логирование

```python
from iflib_tools import AppLogger

# Создание логгера
logger = AppLogger(
    name="DataProcessor",
    component="etl",
    version="1.0.0"
)

# Различные уровни логирования
logger.debug("Отладочная информация", query=sql_query, params=params)
logger.info("Запуск обработки", file_count=100, total_size="2.5MB")
logger.warning("Необычная ситуация", retry_count=3)
logger.error("Ошибка обработки", error=exception, record_id=123)

# Логирование с маскировкой данных
logger.info(
    "API запрос", 
    url="https://api.com/data",
    headers={"Authorization": "Bearer secret_token"},  # Автоматически маскируется
    body={"password": "my_password"}  # Автоматически маскируется
)
```

**Особенности логирования:**
- ✅ Автоматическая маскировка чувствительных данных
- ✅ Цветной вывод в консоль
- ✅ Ротация лог-файлов
- ✅ Структурированный JSON вывод
- ✅ Поддержка экстра-полей
- ✅ Трассировка стека для ошибок

## 🗄️ Модуль базы данных (database)

### Database - универсальный обработчик БД

```python
from iflib_tools import Database

# Подключение к различным СУБД
postgres_db = Database(
    "postgresql://user:pass@localhost:5432/mydb",
    db_type="postgresql"
)

mysql_db = Database(
    "mysql://user:pass@localhost:3306/mydb",
    db_type="mysql"
)

mssql_db = Database(
    "mssql+pyodbc://user:pass@localhost:1433/mydb",
    db_type="mssql"
)

# Автоопределение типа БД
auto_db = Database("postgresql://...", db_type="auto")
```

### Выполнение запросов

```python
# SELECT запросы
result = db.exec(
    "SELECT * FROM users WHERE age > :age AND status = :status",
    {"age": 18, "status": "active"}
)

if result.success:
    for user in result.data:
        print(f"User: {user['name']}, Age: {user['age']}")

# INSERT с возвратом ID
insert_result = db.insert(
    "users", 
    {"name": "John", "email": "john@example.com", "age": 25},
    return_id=True
)

if insert_result.success:
    user_id = insert_result.data['id']  # PostgreSQL: RETURNING, MySQL: LAST_INSERT_ID()
    print(f"Создан пользователь с ID: {user_id}")

# UPDATE
update_result = db.update(
    "users",
    {"status": "inactive", "updated_at": "2024-01-01"},
    "id = :user_id",
    {"user_id": 123}
)

print(f"Обновлено записей: {update_result.rowcount}")

# Специализированные методы
user = db.fetch_one("SELECT * FROM users WHERE id = :id", {"id": 1})
all_users = db.fetch_all("SELECT * FROM users LIMIT 100")
```

### Работа с сессиями

```python
# Контекстный менеджер для транзакций
with db.session() as session:
    try:
        # Выполнение операций в транзакции
        session.execute(text("INSERT INTO logs (message) VALUES (:msg)"), {"msg": "Start"})
        session.execute(text("UPDATE counters SET value = value + 1 WHERE name = 'requests'"))
        # Автоматический коммит при успехе
    except Exception:
        # Автоматический роллбэк при ошибке
        raise

# Проверка соединения
if db.test_connection():
    print("Соединение с БД установлено")
else:
    print("Ошибка подключения к БД")
```

### DatabaseManager - управление несколькими БД

```python
from iflib_tools import db_manager

# Добавление баз данных
main_db = db_manager.add_database(
    name="primary",
    connection_string="postgresql://user:pass@primary-db:5432/app",
    db_type="postgresql",
    set_default=True
)

replica_db = db_manager.add_database(
    name="replica", 
    connection_string="postgresql://user:pass@replica-db:5432/app",
    db_type="postgresql"
)

# Использование
result = db_manager.query(
    "SELECT COUNT(*) as count FROM users",
    db_name="primary"  # Если не указан, используется default
)

# Получение конкретной БД
analytics_db = db_manager.get_database("analytics")
```

## 🌐 Модуль HTTP (http)

### HttpClient - продвинутый HTTP клиент

```python
from iflib_tools import HttpClient

# Создание клиента
client = HttpClient(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3,
    backoff_factor=1.0
)

# Выполнение запросов
response = client.get(
    "/users",
    params={"active": True, "limit": 100},
    headers={"Authorization": "Bearer token"}
)

if response and response.status_code == 200:
    data = response.json()
    print(f"Получено пользователей: {len(data)}")

# POST запрос
client.post(
    "/users",
    json={"name": "John", "email": "john@example.com"},
    headers={"Content-Type": "application/json"}
)

# PUT и DELETE
client.put("/users/123", json={"status": "inactive"})
client.delete("/users/456")

# Получение статистики
stats = client.get_stats()
print(f"""
Статистика запросов:
- Успешных: {stats['success']}
- Ошибок: {stats['errors']}
- Общее время: {stats['total_time']:.2f}s
- Среднее время: {stats['average_time_sec']}s
- Успешность: {stats['success_rate']:.1f}%
""")
```

### HttpManager - управление клиентами

```python
from iflib_tools import HttpManager

manager = HttpManager()

# Получение клиентов для разных API
main_api = manager.get_client(
    base_url="https://api.company.com/v1",
    timeout=30,
    max_retries=3
)

auth_api = manager.get_client(
    base_url="https://auth.company.com",
    timeout=10,
    max_retries=1
)

# Использование
user_data = main_api.get("/users/123").json()
auth_token = auth_api.post("/login", json={"user": "name", "pass": "secret"}).json()
```

## 📨 Модуль Kafka (kafka)

### KafkaProducerWrapper - отправка сообщений

```python
from iflib_tools import KafkaProducerWrapper

# Создание producer'а
producer = KafkaProducerWrapper(
    topic="app-events",
    bootstrap_servers="kafka1:9092,kafka2:9092",
    extra_conf={
        'compression.type': 'gzip',
        'batch.size': 16384
    }
)

# Отправка сообщений
success = producer.send({
    "event_type": "user_created",
    "user_id": 123,
    "timestamp": "2024-01-01T10:00:00Z",
    "metadata": {"source": "web"}
})

if success:
    print("Сообщение отправлено")

# Отправка сырого JSON
producer.send('{"type": "ping", "time": 1234567890}')

# Получение статистики
stats = producer.get_stats()
print(f"Отправлено: {stats['success']} успешно, {stats['failed']} с ошибками")

# Принудительная отправка буферизованных сообщений
remaining = producer.flush(timeout=10.0)
print(f"Осталось сообщений в буфере: {remaining}")
```

### KafkaConsumerWrapper - чтение сообщений

```python
from iflib_tools import KafkaConsumerWrapper

# Создание consumer'а
consumer = KafkaConsumerWrapper(
    topic="app-events",
    bootstrap_servers="kafka1:9092,kafka2:9092",
    group_id="event-processor",
    auto_offset_reset="earliest",  # или 'latest'
    pool_timeout=1.0,
    enable_auto_commit=True
)

# Чтение сообщений
for message in consumer.consume():
    if message is None:
        # Таймаут - нет новых сообщений
        continue
    
    try:
        data = json.loads(message)
        print(f"Обработка события: {data['event_type']}")
        
        # Обработка сообщения...
        process_event(data)
        
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга сообщения: {e}")
    except KeyboardInterrupt:
        print("Завершение по запросу пользователя")
        break

# Consumer автоматически закрывается при выходе из контекста
```

### KafkaManager - централизованное управление

```python
from iflib_tools import KafkaManager

# Создание менеджера
kafka_manager = KafkaManager(
    bootstrap_servers="kafka1:9092,kafka2:9092",
    default_conf={'compression.type': 'gzip'}
)

# Упрощенная отправка
success = kafka_manager.send_message(
    topic="app-events",
    data={"event": "test", "value": 123}
)

# Получение producer'а с reuse
events_producer = kafka_manager.get_producer(
    topic="app-events",
    reuse=True,  # Переиспользование существующего
    extra_conf={'batch.size': 32768}
)

# Получение consumer'а
events_consumer = kafka_manager.get_consumer(
    topic="app-events",
    group_id="processor-v2",
    auto_offset_reset="latest"
)

# Использование контекстного менеджера
with kafka_manager:
    for i in range(100):
        kafka_manager.send_message("app-events", {"number": i})
    # При выходе все клиенты автоматически закрываются

# Статистика по всем клиентам
stats = kafka_manager.get_stats()
print(f"Активных producers: {stats['producers_count']}")
print(f"Активных consumers: {stats['consumers_count']}")
```

## 🛠️ Модуль утилит (utils)

### DataUtils - работа с данными

```python
from iflib_tools import data_utils

# Разбиение на чанки
large_list = list(range(1000))
for chunk in data_utils.chunker(large_list, chunk_size=100):
    print(f"Обработка чанка из {len(chunk)} элементов")
    # Обработка чанка...

# Генерация диапазона дат
dates = data_utils.date_range(
    start_date="2024-01-01",
    end_date="2024-01-07",
    date_format="%Y-%m-%d"
)
# [datetime(2024, 1, 1), datetime(2024, 1, 2), ...]

# Безопасный парсинг JSON
data = data_utils.safe_json_loads('{"key": "value"}')  # {'key': 'value'}
invalid = data_utils.safe_json_loads('invalid', default={})  # {}

# Конвертация DataFrame в records
import pandas as pd
df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
records = data_utils.df_to_records(df)  # [{'A': 1, 'B': 'x'}, {'A': 2, 'B': 'y'}]
```

### ValidationUtils - валидация данных

```python
from iflib_tools import validation_utils

# Валидация email
emails = [
    "valid@example.com",      # ✅ True
    "invalid.email",          # ❌ False
    "name@domain.co.uk",      # ✅ True
    "test@sub.domain.com"     # ✅ True
]

for email in emails:
    if validation_utils.is_valid_email(email):
        print(f"✅ Valid email: {email}")
    else:
        print(f"❌ Invalid email: {email}")

# Валидация телефонов (российский формат)
phones = [
    "+79161234567",      # ✅ True
    "89161234567",       # ✅ True  
    "9161234567",        # ✅ True
    "+7 (916) 123-45-67", # ✅ True
    "1234567890"         # ❌ False
]

for phone in phones:
    if validation_utils.is_valid_phone(phone):
        print(f"✅ Valid phone: {phone}")
    else:
        print(f"❌ Invalid phone: {phone}")
```

### FormatUtils - форматирование данных

```python
from iflib_tools import format_utils

# Форматирование размеров
sizes = [1024, 1024**2, 1024**3, 1024**4]
for size in sizes:
    formatted = format_utils.format_bytes(size)
    print(f"{size} bytes = {formatted}")
    # 1024 bytes = 1.00 KB
    # 1048576 bytes = 1.00 MB  
    # 1073741824 bytes = 1.00 GB
    # 1099511627776 bytes = 1.00 TB

# Форматирование длительности
durations = [0.125, 1.5, 65.7, 125.3, 3665.8]
for duration in durations:
    formatted = format_utils.format_duration(duration)
    print(f"{duration}s = {formatted}")
    # 0.125s = 125ms
    # 1.5s = 1.5s
    # 65.7s = 1m 5s  
    # 125.3s = 2m 5s
    # 3665.8s = 61m 5s
```

## 🔄 Интеграция модулей

### Полный пример приложения

```python
from iflib_tools import (
    config_manager, AppLogger, db_manager, 
    HttpManager, KafkaManager, data_utils
)
import json

class DataProcessingService:
    def __init__(self, config_path: str):
        # Загрузка конфигурации
        config_manager.load_from_yaml(config_path)
        self.config = config_manager.config
        
        # Инициализация логгера
        self.logger = AppLogger(
            name=self.config.application.name,
            component="data_processor",
            environment=self.config.application.env
        )
        
        # Настройка базы данных
        self._setup_database()
        
        # HTTP клиент для внешних API
        self.http_client = HttpManager().get_client(
            base_url=self.config.api.base_url,
            timeout=self.config.api.timeout
        )
        
        # Kafka для событий
        self.kafka_manager = KafkaManager(
            bootstrap_servers=self.config.kafka.bootstrap_servers
        )
        
        self.logger.info("Сервис инициализирован", config_source=config_path)
    
    def _setup_database(self):
        """Настройка подключений к базам данных"""
        # Основная база
        db_manager.add_database(
            name="primary",
            connection_string=self.config.databases.primary.get_connection_string(),
            db_type="postgresql",
            set_default=True
        )
        
        # База для аналитики
        if hasattr(self.config.databases, 'analytics'):
            db_manager.add_database(
                name="analytics",
                connection_string=self.config.databases.analytics.get_connection_string(),
                db_type="postgresql"
            )
    
    def process_user_batch(self, user_ids: list):
        """Обработка батча пользователей"""
        self.logger.info(
            "Начало обработки батча пользователей",
            user_count=len(user_ids),
            batch_id=id(user_ids)
        )
        
        # Разбиение на чанки
        for chunk in data_utils.chunker(user_ids, chunk_size=100):
            try:
                self._process_chunk(chunk)
                
                # Отправка события в Kafka
                self.kafka_manager.send_message(
                    self.config.kafka.topics.processing_events,
                    {
                        "event_type": "batch_processed",
                        "user_count": len(chunk),
                        "timestamp": data_utils.get_current_iso_time()
                    }
                )
                
            except Exception as e:
                self.logger.error(
                    "Ошибка обработки чанка",
                    error=e,
                    chunk_size=len(chunk),
                    first_user=chunk[0] if chunk else None
                )
    
    def _process_chunk(self, user_chunk: list):
        """Обработка одного чанка пользователей"""
        # Получение данных из БД
        placeholders = ', '.join([':id_' + str(i) for i in range(len(user_chunk))])
        params = {f'id_{i}': user_id for i, user_id in enumerate(user_chunk)}
        
        result = db_manager.query(
            f"SELECT * FROM users WHERE id IN ({placeholders})",
            params=params
        )
        
        if not result.success:
            raise Exception(f"Database error: {result.error}")
        
        # Обновление через HTTP API
        for user in result.data:
            response = self.http_client.put(
                f"/users/{user['id']}",
                json={"processed": True, "processed_at": data_utils.get_current_iso_time()}
            )
            
            if not response or response.status_code != 200:
                self.logger.warning(
                    "Не удалось обновить пользователя через API",
                    user_id=user['id'],
                    status_code=response.status_code if response else 'No response'
                )

# Использование
if __name__ == "__main__":
    service = DataProcessingService("config/production.yaml")
    
    # Пример обработки
    user_ids = list(range(1, 1001))
    service.process_user_batch(user_ids)
```

## 🔧 Переменные окружения

Библиотека поддерживает переопределение настроек через environment variables:

```bash
# База данных
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=secret_password
export DB_NAME=myapp
export DB_TYPE=postgresql
export DB_DRIVER=psycopg2

# Логирование
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json

# HTTP
export SERVER_URL=https://api.example.com
export HTTP_TIMEOUT=30
export HTTP_MAX_RETRIES=3

# Kafka
export KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092
export KAFKA_GROUP_ID=my-consumer-group

# Приложение
export APP_ENV=production
export APP_NAME=MyService
```

## 📊 Мониторинг и метрики

Каждый модуль предоставляет статистику работы:

```python
# Статистика HTTP запросов
http_stats = http_client.get_stats()

# Статистика Kafka
kafka_stats = kafka_manager.get_stats()

# Статистика базы данных
db_stats = db.get_stats()  # В разработке

print(f"""
📊 Статистика системы:
HTTP: {http_stats['success']}/{http_stats['total_requests']} запросов 
      ({http_stats['success_rate']:.1f}% успешных)
Kafka: {kafka_stats['producers_count']} producers, 
       {kafka_stats['consumers_count']} consumers
""")
```

## 🔒 Безопасность

- **Маскировка данных**: Автоматическое скрытие паролей, токенов в логах
- **Валидация входных данных**: Проверка email, телефонов и других данных
- **Экранирование SQL**: Использование параметризованных запросов
- **Безопасные парсеры**: Обработка JSON с обработкой ошибок
- **Таймауты**: Предотвращение зависаний в сетевых операциях

## 🐛 Отладка и troubleshooting

### Включение детального логирования

```python
from iflib_tools import LoggerSetup

# Максимальная детализация
log_setup = LoggerSetup(level="TRACE")

# Или через конфигурацию
config_manager.load_from_dict({
    'application': {
        'logger': {'level': 'TRACE'}  # DEBUG, INFO, WARNING, ERROR
    }
})
```

### Диагностика проблем с БД

```python
# Проверка подключения
if not db.test_connection():
    print("❌ Нет подключения к БД")
    
# Проверка существования таблицы
if db.table_exists('users'):
    print("✅ Таблица users существует")
    
# Получение списка колонок
columns = db.get_table_columns('users')
print(f"Колонки таблицы users: {columns}")

# Проверка версии MySQL
if db.db_type == "mysql":
    version = db.get_mysql_version()
    print(f"Версия MySQL: {version}")
```

### Обработка ошибок Kafka

```python
try:
    producer.send({"event": "test"})
except BufferError as e:
    print("Буфер Kafka переполнен, попробуйте позже")
except Exception as e:
    print(f"Критическая ошибка Kafka: {e}")
    
# Мониторинг статуса отправки
stats = producer.get_stats()
if stats['failed'] > 0:
    print(f"Внимание: {stats['failed']} сообщений не доставлено")
```

## 📈 Производительность

### Оптимизация пула соединений БД

```python
db = Database(
    connection_string="postgresql://...",
    db_type="postgresql",
    pool_size=20,           # Размер пула
    max_overflow=30,        # Максимальное переполнение
    pool_pre_ping=True,     # Проверка соединений
    pool_recycle=3600       # Переподключение каждый час
)
```

### Настройка Kafka для высокой нагрузки

```python
producer = KafkaProducerWrapper(
    topic="high-volume-events",
    bootstrap_servers="kafka:9092",
    extra_conf={
        'batch.size': 65536,           # Размер батча
        'linger.ms': 100,              # Задержка отправки
        'compression.type': 'snappy',  # Сжатие
        'acks': 'all'                  # Подтверждение
    }
)
```

## 🤝 Совместимость

- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Базы данных**: PostgreSQL 12+, MySQL 8.0+, MSSQL 2016+
- **Kafka**: Apache Kafka 2.5+
- **HTTP**: requests 2.25+

## 📄 Лицензия

MIT License - свободное использование, модификация и распространение.

---

**Примечание**: Эта документация охватывает все основные возможности библиотеки. Каждый модуль можно использовать независимо или в комбинации с другими в зависимости от потребностей вашего проекта.