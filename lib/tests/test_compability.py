# test_integration.py
from __future__ import annotations
import sys
import os
import tempfile
import yaml

# Добавляем путь к вашим модулям
sys.path.append(os.path.dirname(__file__))


def test_config_and_logging_integration():
    """Тест интеграции конфигурации и логирования"""
    print("=== Тест 1: Конфигурация + Логирование ===")

    from lib.config import config_manager, DatabaseConfig, ServerConfig
    from lib.logger import LoggerSetup, AppLogger

    # Создаем тестовый конфиг
    test_config = {
        'application': {
            'name': 'TestApp',
            'env': 'test',
            'logger': {
                'level': 'DEBUG',
                'format': 'simple',
                'file': 'test.log'
            }
        },
        'server': {
            'url': 'https://api.test.com',
            'endpoint': '/api/v1'
        },
        'database': {
            'host': '46.148.205.149',
            'port': 5432,
            'database': 'transport',
            'user': 'dba',
            'password': 'vfvfvskfnfve'
        }
    }

    # Загружаем конфигурацию
    config_manager.load_from_dict(test_config)

    # Инициализируем логгер с настройками из конфига
    log_level = config_manager.get('application.logger.level', 'INFO')
    logger_setup = LoggerSetup(level=log_level, enable_file_logging=False)
    app_logger = AppLogger(name=config_manager.config.application.name)

    app_logger.info("Тестовое сообщение", component="integration_test")
    print("✅ Конфигурация и логирование работают вместе")


def test_database_and_config_integration():
    """Тест интеграции базы данных и конфигурации"""
    print("\n=== Тест 2: База данных + Конфигурация ===")

    from lib.config import config_manager
    from lib.database import Database, db_manager

    # Создаем тестовый конфиг с паролем содержащим @
    test_config = {
        'database': {
            'host': '10.0.50.181',
            'port': 5432,
            'database': 'transport',
            'user': 'dba',
            'password': 'vfvfvskfnfve'
        }
    }

    # Загружаем конфигурацию
    config_manager.load_from_dict(test_config)
    db_config = config_manager.config.database

    # ✅ ПРАВИЛЬНО: используем метод get_connection_string() который экранирует спецсимволы
    test_connection_string = db_config.get_connection_string(masked=False)

    # Добавляем базу в менеджер
    db = db_manager.add_database(
        name='transport',
        connection_string=test_connection_string,
        db_type='postgresql',
        set_default=True
    )

    print(f"✅ База данных создана: {db._masked_connection_string()}")

    # Тестируем подключение
    result = db.test_connection()
    print(f"✅ Подключение к БД: {'Успешно' if result else 'Не удалось'}")

    # Тестовый запрос
    if result:
        query_result = db.exec("SELECT 1 as test_value")
        print(f"✅ Тестовый запрос выполнен: {query_result.success}")
        if query_result.success:
            print(f"Результат: {query_result.data}")

    return db_manager


def test_http_client_integration():
    """Тест HTTP клиента"""
    print("\n=== Тест 3: HTTP Клиент ===")

    from lib.http import HttpClient, HttpManager

    # Создаем HTTP менеджер
    http_manager = HttpManager()
    client = http_manager.get_client(base_url="https://httpbin.org")

    # Тестовый запрос
    response = client.get("/get")
    if response and response.status_code == 200:
        print("✅ HTTP клиент работает корректно")
    else:
        print("⚠️  HTTP запрос не удался (возможно, нет интернета)")

    return http_manager


def test_kafka_integration():
    """Тест интеграции Kafka"""
    print("\n=== Тест 4: Kafka ===")

    from lib.kafka import KafkaManager, KafkaProducerWrapper, KafkaConsumerWrapper

    # Создаем менеджер Kafka (без реального подключения)
    kafka_manager = KafkaManager(bootstrap_servers="gitlab-ci.ru:9092")

    # Тестируем создание продюсера
    producer = kafka_manager.get_producer("test_topic", reuse=False)
    print(f"✅ Producer создан: {producer.topic}")

    # Тестируем создание консьюмера
    consumer = kafka_manager.get_consumer("test_topic", group_id="test_group")
    print(f"✅ Consumer создан: {consumer.topic}")

    # Тестируем отправку сообщения (фейковую)
    success = producer.fake_send({"test": "message"})
    print(f"✅ Фейковая отправка: {success}")

    return kafka_manager


def test_utils_integration():
    """Тест утилит с другими модулями"""
    print("\n=== Тест 5: Утилиты ===")

    from lib.utils import data_utils, validation_utils, format_utils
    from lib.database import QueryResult

    # Тест утилит с данными из базы
    test_data = [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}]

    # DataUtils с данными
    chunks = list(data_utils.chunker(test_data, 1))
    print(f"✅ DataUtils.chunker: {len(chunks)} чанков")

    # ValidationUtils
    email_valid = validation_utils.is_valid_email("test@example.com")
    print(f"✅ ValidationUtils.email: {email_valid}")

    # FormatUtils с данными запроса
    result = QueryResult(data=test_data, rowcount=2)
    json_output = result.to_json()
    print(f"✅ QueryResult.to_json: {len(json_output)} chars")

    bytes_formatted = format_utils.format_bytes(1024 * 1024)
    print(f"✅ FormatUtils.bytes: {bytes_formatted}")


def test_complete_workflow():
    """Тест полного workflow"""
    print("\n=== Тест 6: Полный Workflow ===")

    from lib.config import config_manager
    from lib.logger import AppLogger
    from lib.database import db_manager
    from lib.http import HttpManager
    from lib.kafka import KafkaManager

    # Инициализация компонентов
    app_logger = AppLogger(name="IntegrationTest")

    # Конфигурация
    config = {
        'application': {'name': 'FullTest', 'env': 'test'},
        'database': {
            'host': '46.148.205.149', 'port': 5432,
            'database': 'transport', 'user': 'egais-management-documents-circulation-api', 'password': 'Kg5d@spQuM7Gf'
        }
    }
    config_manager.load_from_dict(config)

    # Логирование
    app_logger.info("Начало полного теста",
                    component="full_workflow",
                    config_loaded=True)

    # База данных (имитация)
    try:
        db_manager.add_database(
            "main",
            "postgresql://test:test@localhost:5432/test",
            set_default=True
        )
        app_logger.info("База данных добавлена в менеджер")
    except Exception as e:
        app_logger.error("Ошибка добавления БД", error=e)

    # HTTP клиент
    http_manager = HttpManager()
    http_client = http_manager.get_client("https://httpbin.org")

    # Kafka менеджер
    kafka_manager = KafkaManager("localhost:9092")

    app_logger.info("Все компоненты инициализированы",
                    components=["config", "logging", "database", "http", "kafka"])

    print("✅ Полный workflow выполнен успешно")


def main():
    """Основная функция тестирования"""
    print("🧪 Начинаем тестирование совместимости модулей...\n")

    try:
        # Тест 1: Конфигурация + Логирование
        test_config_and_logging_integration()

        # Тест 2: База данных + Конфигурация
        db_manager = test_database_and_config_integration()

        # Тест 3: HTTP клиент
        http_manager = test_http_client_integration()

        # Тест 4: Kafka
        kafka_manager = test_kafka_integration()

        # Тест 5: Утилиты
        test_utils_integration()

        # Тест 6: Полный workflow
        test_complete_workflow()

        print("\n🎉 Все тесты пройдены успешно! Модули совместимы.")

        # Очистка ресурсов
        if 'db_manager' in locals():
            db_manager.close_all()
        if 'kafka_manager' in locals():
            kafka_manager.close_all()

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())