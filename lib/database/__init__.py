from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from loguru import logger
from sqlalchemy import create_engine, text, CursorResult, Row
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import json
from dataclasses import dataclass
from datetime import datetime
import re

Base = declarative_base()


@dataclass
class QueryResult:
    """Результат запроса в виде объекта"""
    data: Optional[Union[Dict, List[Dict]]]
    rowcount: int = 0
    success: bool = True
    error: Optional[str] = None

    def to_json(self) -> str:
        """Конвертирует результат в JSON строку"""
        return json.dumps(self.data, ensure_ascii=False, default=str)

    @property
    def is_empty(self) -> bool:
        """Проверяет пустой ли результат"""
        if self.data is None:
            return True
        if isinstance(self.data, list):
            return len(self.data) == 0
        return False


class Database:
    """
    Универсальный обработчик для PostgreSQL, MySQL и MSSQL на основе SQLAlchemy
    """

    def __init__(self, connection_string: str, db_type: str = "auto", **kwargs):
        """
        :param connection_string: строка подключения
        :param db_type: "postgresql", "mysql", "mssql" или "auto" для автоопределения
        """
        self.connection_string = connection_string
        self.db_type = self._detect_db_type(connection_string) if db_type == "auto" else db_type

        # Параметры подключения для разных СУБД
        engine_kwargs = self._get_engine_kwargs(**kwargs)

        self.engine = create_engine(connection_string, **engine_kwargs)
        self.session_factory = sessionmaker(bind=self.engine)
        self.ScopedSession = scoped_session(self.session_factory)

        logger.info(f"Database connection initialized: {self._masked_connection_string()} ({self.db_type})")

    def _detect_db_type(self, connection_string: str) -> str:
        """Автоопределение типа базы по строке подключения"""
        connection_string_lower = connection_string.lower()

        if connection_string_lower.startswith('postgresql://'):
            return "postgresql"
        elif connection_string_lower.startswith('mysql://') or connection_string_lower.startswith('mysql+pymysql://'):
            return "mysql"
        elif any(prefix in connection_string_lower for prefix in ['mssql://', 'sqlserver://', 'mssql+pyodbc://']):
            return "mssql"
        else:
            logger.warning("Cannot detect database type, defaulting to PostgreSQL")
            return "postgresql"

    def _get_engine_kwargs(self, **kwargs) -> Dict:
        """Возвращает параметры движка для конкретной СУБД"""
        base_kwargs = {
            'poolclass': QueuePool,
            'pool_size': 10,
            'max_overflow': 20,
            'pool_pre_ping': True,
            'echo': False,
            'json_serializer': lambda obj: json.dumps(obj, ensure_ascii=False, default=str),
        }

        # Специфичные настройки для MSSQL
        if self.db_type == "mssql":
            base_kwargs.update({
                'pool_pre_ping': True,
                'connect_args': {
                    'timeout': 30,
                    'autocommit': False,
                }
            })
        # Специфичные настройки для MySQL
        elif self.db_type == "mysql":
            base_kwargs.update({
                'pool_pre_ping': True,
                'pool_recycle': 3600,  # Переподключаться каждый час
                'connect_args': {
                    'charset': 'utf8mb4',
                    'autocommit': False,
                }
            })

        base_kwargs.update(kwargs)
        return base_kwargs

    def _masked_connection_string(self) -> str:
        """Возвращает замаскированную строку подключения для логов"""
        # Маскируем логин и пароль в любой строке подключения
        pattern = r'://([^:]+):([^@]+)@'
        replacement = r'://***:***@'
        return re.sub(pattern, replacement, self.connection_string)

    @contextmanager
    def session(self):
        """Контекстный менеджер для сессий"""
        session = self.ScopedSession()
        try:
            yield session
            session.commit()
            logger.debug("Session committed successfully")
        except Exception as ex:
            session.rollback()
            logger.error(f"Session rollback due to error: {ex}")
            raise
        finally:
            session.close()
            self.ScopedSession.remove()

    def exec(self, query: str, params: Dict = None) -> QueryResult:
        """
        Универсальный метод выполнения запросов для всех СУБД
        """
        logger.trace(f"Executing query: {query}")

        try:
            with self.engine.connect() as connection:
                # Адаптируем запрос для конкретной СУБД если нужно
                if self.db_type == "mssql":
                    query = self._adapt_query_for_mssql(query)
                elif self.db_type == "mysql":
                    query = self._adapt_query_for_mysql(query)

                # Выполняем запрос
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))

                # Определяем тип запроса
                query_type = query.strip().upper().split()[0]

                if query_type in ('SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN'):
                    # SELECT и информационные запросы - возвращаем данные
                    rows = result.fetchall()
                    data = self._rows_to_dict(rows, result.keys())
                    return QueryResult(data, len(rows))

                else:
                    # INSERT, UPDATE, DELETE - возвращаем количество affected rows
                    connection.commit()
                    return QueryResult(None, result.rowcount)

        except Exception as ex:
            logger.error(f"Error executing query: {query}\nError: {ex}")
            return QueryResult(None, 0, False, str(ex))

    def _adapt_query_for_mssql(self, query: str) -> str:
        """Адаптирует PostgreSQL-специфичный синтаксис для MSSQL"""
        # LIMIT -> TOP для простых случаев
        if ' LIMIT ' in query.upper() and 'SELECT' in query.upper():
            query = re.sub(
                r'LIMIT\s+(\d+)',
                r'TOP \1',
                query,
                flags=re.IGNORECASE
            )

        # Заменяем ILIKE на LIKE для MSSQL
        if ' ILIKE ' in query.upper():
            query = query.replace(' ILIKE ', ' LIKE ')

        return query

    def _adapt_query_for_mysql(self, query: str) -> str:
        """Адаптирует запросы для MySQL"""
        # Заменяем ILIKE на LIKE для MySQL (MySQL LIKE по умолчанию регистронезависим)
        if ' ILIKE ' in query.upper():
            query = query.replace(' ILIKE ', ' LIKE ')

        # Заменяем ::text на CAST для MySQL
        query = re.sub(
            r'::\w+',
            lambda m: f'CAST({m.group(0)[2:]} AS CHAR)',
            query
        )

        return query

    def fetch_one(self, query: str, params: Dict = None) -> QueryResult:
        """Выполняет запрос и возвращает первую строку"""
        # Для MSSQL добавляем TOP 1 если это SELECT без LIMIT/TOP
        if (self.db_type == "mssql" and
                query.strip().upper().startswith('SELECT') and
                ' TOP ' not in query.upper() and
                ' LIMIT ' not in query.upper()):
            query = re.sub(r'^SELECT', 'SELECT TOP 1', query, flags=re.IGNORECASE)
        # Для MySQL и PostgreSQL добавляем LIMIT 1
        elif (self.db_type in ["mysql", "postgresql"] and
              query.strip().upper().startswith('SELECT') and
              ' LIMIT ' not in query.upper()):
            query = query + ' LIMIT 1'

        result = self.exec(query, params)
        if result.success and isinstance(result.data, list) and result.data:
            result.data = result.data[0]
        return result

    def fetch_all(self, query: str, params: Dict = None) -> QueryResult:
        """Выполняет запрос и возвращает все строки"""
        return self.exec(query, params)

    def insert(self, table: str, data: Dict, return_id: bool = False) -> QueryResult:
        """
        Вставка одной записи с поддержкой RETURNING для PostgreSQL,
        LAST_INSERT_ID() для MySQL и OUTPUT для MSSQL
        """
        columns = ', '.join(data.keys())
        values = ', '.join([f':{key}' for key in data.keys()])

        if return_id:
            if self.db_type == "postgresql":
                query = f"INSERT INTO {table} ({columns}) VALUES ({values}) RETURNING id"
            elif self.db_type == "mysql":
                query = f"INSERT INTO {table} ({columns}) VALUES ({values})"
            else:  # MSSQL
                query = f"INSERT INTO {table} ({columns}) OUTPUT INSERTED.id VALUES ({values})"
        else:
            query = f"INSERT INTO {table} ({columns}) VALUES ({values})"

        result = self.exec(query, data)

        # Для MySQL получаем последний вставленный ID отдельным запросом
        if return_id and self.db_type == "mysql" and result.success:
            last_id_result = self.fetch_one("SELECT LAST_INSERT_ID() as id")
            if last_id_result.success:
                result.data = last_id_result.data

        return result

    def update(self, table: str, data: Dict, where: str, where_params: Dict = None) -> QueryResult:
        """Обновление записей"""
        set_clause = ', '.join([f"{key} = :{key}" for key in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"

        params = data.copy()
        if where_params:
            params.update(where_params)

        return self.exec(query, params)

    def _rows_to_dict(self, rows: List[Row], keys: List[str]) -> List[Dict]:
        """Конвертирует строки в список словарей"""
        if not rows:
            return []

        return [dict(zip(keys, row)) for row in rows]

    def table_exists(self, table_name: str) -> bool:
        """Проверяет существование таблицы"""
        if self.db_type == "postgresql":
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """
        elif self.db_type == "mysql":
            query = """
                SELECT COUNT(*) as table_exists
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = :table_name
            """
        else:  # MSSQL
            query = """
                SELECT CASE 
                    WHEN EXISTS (
                        SELECT * FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_NAME = :table_name
                    ) THEN 1 ELSE 0 END AS table_exists
            """

        result = self.fetch_one(query, {'table_name': table_name})
        if not result.success:
            return False

        if self.db_type == "postgresql":
            return result.data['exists']
        elif self.db_type == "mysql":
            return result.data['table_exists'] > 0
        else:  # MSSQL
            return result.data['table_exists'] == 1

    def get_table_columns(self, table_name: str) -> List[str]:
        """Возвращает список колонок таблицы"""
        if self.db_type == "postgresql":
            query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :table_name
                ORDER BY ordinal_position
            """
        elif self.db_type == "mysql":
            query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() AND table_name = :table_name
                ORDER BY ordinal_position
            """
        else:  # MSSQL
            query = """
                SELECT COLUMN_NAME as column_name
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = :table_name
                ORDER BY ORDINAL_POSITION
            """

        result = self.fetch_all(query, {'table_name': table_name})
        return [row['column_name'] for row in result.data] if result.success else []

    def test_connection(self) -> bool:
        """Проверяет соединение с базой данных"""
        try:
            with self.engine.connect() as conn:
                if self.db_type == "mysql":
                    conn.execute(text("SELECT 1"))
                else:
                    conn.execute(text("SELECT 1"))
            logger.info("Database connection test: OK")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def get_mysql_version(self) -> Optional[str]:
        """Возвращает версию MySQL сервера (только для MySQL)"""
        if self.db_type != "mysql":
            logger.warning("This method is only available for MySQL databases")
            return None

        result = self.fetch_one("SELECT VERSION() as version")
        return result.data['version'] if result.success else None

    def list_databases(self) -> List[str]:
        """Возвращает список баз данных (только для MySQL)"""
        if self.db_type != "mysql":
            logger.warning("This method is only available for MySQL databases")
            return []

        result = self.fetch_all("SHOW DATABASES")
        return [row['Database'] for row in result.data] if result.success else []


class DatabaseManager:
    """
    Менеджер для работы с несколькими базами данных разных типов
    """

    def __init__(self):
        self.databases: Dict[str, Database] = {}
        self.default_db: Optional[str] = None

    def add_database(self, name: str, connection_string: str, db_type: str = "auto",
                     set_default: bool = False, **kwargs) -> Database:
        """
        Добавляет базу данных в менеджер
        """
        db = Database(connection_string, db_type, **kwargs)
        self.databases[name] = db

        if set_default or self.default_db is None:
            self.default_db = name

        logger.info(f"Database '{name}' added to manager (type: {db.db_type})")
        return db

    def get_database(self, name: str = None) -> Database:
        """Возвращает базу данных по имени или default"""
        db_name = name or self.default_db
        if db_name not in self.databases:
            raise ValueError(f"Database '{db_name}' not found")
        return self.databases[db_name]

    def query(self, query: str, params: Dict = None, db_name: str = None) -> QueryResult:
        """Упрощенный интерфейс для выполнения запросов"""
        db = self.get_database(db_name)
        return db.exec(query, params)

    def close_all(self):
        """Закрывает все соединения с базами данных"""
        for name, db in self.databases.items():
            try:
                db.engine.dispose()
                logger.debug(f"Database '{name}' connection closed")
            except Exception as e:
                logger.error(f"Error closing database '{name}': {e}")


# Глобальный менеджер баз данных
db_manager = DatabaseManager()

# Aliases для обратной совместимости
PostgresqlDb = Database
MySQLDb = Database
DB = Database
