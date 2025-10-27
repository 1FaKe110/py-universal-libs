
# Python Utilities Library

Набор готовых решений и утилит для быстрого старта Python проектов. Библиотека включает модули для работы с конфигурацией, базами данных, Kafka, HTTP-запросами, логированием и другими часто используемыми функциями.

## Быстрый старт

### Установка зависимостей

```bash
pip install -r requirements.txt
```
Базовая настройка
```python


from lib.config import config_manager
from lib.logger import AppLogger

# Загрузка конфигурации
config_manager.load_from_dict({
    'application': {
        'name': 'MyApp',
        'env': 'development',
        'logger': {'level': 'DEBUG'}
    },
    'database': {
        'host': 'localhost',
        'port': 5432,
        'database': 'myapp',
        'user': 'postgres',
        'password': 'password'
    }
})

# Инициализация логгера
app_logger = AppLogger(name=config_manager.config.application.name)
app_logger.info("Приложение запущено")
```
Структура проекта
```
lib/
├── config/          # Управление конфигурацией
├── database/        # Работа с базами данных (PostgreSQL, MSSQL)
├── http/            # HTTP клиент с retry логикой
├── kafka/           # Producer/Consumer для Apache Kafka
├── logger/          # Настройка логирования
└── utils/           # Вспомогательные утилиты
main.py              # Главный файл
... дальще ваши файлы проекта
```

# Модули
1. Конфигурация (lib.config)
Гибкая система конфигурации с поддержкой YAML, env переменных и маскировкой чувствительных данных.

```python

from lib.config import config_manager

# Загрузка из YAML
config_manager.load_from_yaml("config.yaml")

# Загрузка из словаря
config_manager.load_from_dict({
    'application': {'name': 'TestApp', 'env': 'test'},
    'database': {
        'host': 'localhost', 
        'port': 5432,
        'database': 'test',
        'user': 'user',
        'password': 'pass'
    }
})

# Использование
db_config = config_manager.config.database
connection_string = db_config.get_connection_string(masked=False)

# Получение значений по пути
log_level = config_manager.get('application.logger.level', 'INFO')
```
Пример YAML конфигурации:
```yaml

application:
  name: "My Application"
  env: "development"
  logger:
    level: "DEBUG"
    format: "simple"

server:
  url: "https://api.example.com"
  endpoint: "/api/v1"

database:
  host: "localhost"
  port: 5432
  database: "myapp"
  user: "postgres"
  password: "password"

databases:
  analytics:
    host: "analytics-db.example.com"
    port: 5432
    database: "analytics"
    user: "analytics_user"
    password: "analytics_password"
```

# Логирование (lib.logger)
Мощная система логирования с маскировкой чувствительных данных и структурированным выводом.

```python

from lib.logger import LoggerSetup, AppLogger

# Настройка логгера
log_setup = LoggerSetup(level="DEBUG", enable_file_logging=True)

# Создание логгера приложения
app_logger = AppLogger(name="MyApp", component="main")

# Использование
app_logger.info("Запуск процесса", step="initialization")
app_logger.error("Ошибка обработки", error=exception, data_count=100)
app_logger.debug("Отладочная информация", query=sql_query, params=params)
```
Особенности:
- Автоматическая маскировка паролей и токенов
- Поддержка структурированных данных
- Цветной вывод в консоль
- Ротация лог-файлов

# Базы данных (lib.database)
Универсальный обработчик для PostgreSQL и MSSQL с поддержкой пулинга соединений.

```python

from lib.database import db_manager, Database

# Добавление базы данных
db = db_manager.add_database(
    name="main",
    connection_string="postgresql://user:pass@host:5432/db",
    db_type="postgresql",
    set_default=True
)

# Выполнение запросов
result = db.exec("SELECT * FROM users WHERE age > :age", {"age": 18})

if result.success:
    for user in result.data:
        print(user['name'])

# Использование контекстного менеджера
with db.session() as session:
    # Работа с сессией
    pass

# Вставка данных
insert_result = db.insert("users", {"name": "John", "age": 25}, return_id=True)
if insert_result.success:
    print(f"Создан пользователь с ID: {insert_result.data['id']}")
```
Поддерживаемые СУБД:
```
PostgreSQL
Microsoft SQL Server
Автоопределение типа БД
```

# HTTP клиент (lib.http)
HTTP клиент с retry логикой, таймаутами и подробным логированием.

```python

from lib.http import HttpManager

# Создание менеджера
http_manager = HttpManager()
client = http_manager.get_client(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3
)

# Выполнение запросов
response = client.get("/users", params={"active": True})

if response and response.status_code == 200:
    data = response.json()
    print(f"Получено {len(data)} пользователей")

# POST запрос с данными
client.post("/users", json={"name": "John", "email": "john@example.com"})

# Получение статистики
stats = client.get_stats()
print(f"Успешных запросов: {stats['success_rate']}%")
```

# Kafka (lib.kafka)
Производитель и потребитель для Apache Kafka с управлением соединениями.

```python

from lib.kafka import KafkaManager

# Создание менеджера
kafka_manager = KafkaManager(bootstrap_servers="localhost:9092")

# Отправка сообщений
producer = kafka_manager.get_producer("test-topic")
success = producer.send({"event": "user_created", "user_id": 123})

# Чтение сообщений
consumer = kafka_manager.get_consumer(
    "test-topic", 
    group_id="my-group",
    auto_offset_reset="earliest"
)

for message in consumer.consume():
    if message:
        print(f"Получено сообщение: {message}")

# Использование менеджера для упрощенной отправки
kafka_manager.send_message("test-topic", {"key": "value"})
```

# Утилиты (lib.utils)
Набор полезных утилит для работы с данными.

```python

from lib.utils import data_utils, validation_utils, format_utils

# Работа с данными
chunks = list(data_utils.chunker([1, 2, 3, 4, 5], chunk_size=2))
# [[1, 2], [3, 4], [5]]

dates = data_utils.date_range("2024-01-01", "2024-01-05")
# [datetime(2024, 1, 1), ..., datetime(2024, 1, 5)]

# Валидация
is_valid = validation_utils.is_valid_email("test@example.com")
is_phone_valid = validation_utils.is_valid_phone("+79161234567")

# Форматирование
size_str = format_utils.format_bytes(1024 * 1024)  # "1.00 MB"
duration_str = format_utils.format_duration(125.5)  # "2m 5s"
```


### Тестирование
В проекте предусмотрены интеграционные тесты для проверки совместимости модулей:

```bash
python test_compability.py
```

Тесты проверяют:
- Интеграцию конфигурации и логирования
- Работу с базами данных
- HTTP запросы
- Kafka producers/consumers
- Вспомогательные утилиты

Пример полного workflow
```python

from lib.config import config_manager
from lib.logger import AppLogger
from lib.database import db_manager
from lib.http import HttpManager
from lib.kafka import KafkaManager

class MyApplication:
    def __init__(self):
        self.logger = AppLogger(name="MyApp")
        
        # Загрузка конфигурации
        config_manager.load_from_yaml("config.yaml")
        
        # Инициализация базы данных
        db_config = config_manager.config.database
        db_manager.add_database(
            "main",
            db_config.get_connection_string(),
            set_default=True
        )
        
        # HTTP клиент для внешнего API
        self.http_client = HttpManager().get_client(
            base_url=config_manager.config.server.url
        )
        
        # Kafka для событий
        self.kafka_manager = KafkaManager(
            bootstrap_servers="kafka:9092"
        )
    
    def process_data(self):
        self.logger.info("Начало обработки данных")
        
        # Получение данных из БД
        result = db_manager.query("SELECT * FROM tasks WHERE status = 'pending'")
        
        for task in result.data:
            try:
                # Обработка задачи
                response = self.http_client.post("/process", json=task)
                
                # Отправка события в Kafka
                self.kafka_manager.send_message(
                    "task-events",
                    {"task_id": task['id'], "status": "processed"}
                )
                
                self.logger.info("Задача обработана", task_id=task['id'])
                
            except Exception as e:
                self.logger.error("Ошибка обработки задачи", 
                                error=e, task_id=task['id'])

if __name__ == "__main__":
    app = MyApplication()
    app.process_data()
```
Настройки окружения
Проект поддерживает переопределение настроек через переменные окружения:

```bash

export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=secret
export LOG_LEVEL=DEBUG
export SERVER_URL=https://api.example.com
```
Мониторинг и метрики
Каждый модуль предоставляет статистику работы:

```python

# Статистика HTTP запросов
http_stats = http_client.get_stats()

# Статистика Kafka producer
kafka_stats = producer.get_stats()

# Статистика менеджера БД
db_stats = db_manager.get_stats()
```

# Безопасность
- Автоматическая маскировка чувствительных данных в логах
- Экранирование специальных символов в connection strings
- Валидация входных данных
- Безопасная обработка ошибок
- Совместимость
- Python 3.8+
- PostgreSQL 12+
- MSSQL 2016+
- Apache Kafka 2.5+

# Установка

```bash
pip install git+https://github.com/1FaKe110/py-universal-libs.git
```

# Использование в requirements.txt других проектов:

```txt
loguru==0.7.3
... тут ваши импорты
my-libs @ git+https://github.com/yourusername/py-universal-libs.git@v0.1.0
```

# Лицензия
MIT License - свободное использование и модификация.

Примечание: Это библиотека готовых решений, предназначенная для быстрого старта проектов. Каждый модуль можно использовать независимо или в комбинации с другими.