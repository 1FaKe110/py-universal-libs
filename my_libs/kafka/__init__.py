from __future__ import annotations

import json
import os
import uuid
from time import sleep
from loguru import logger
from typing import Dict, Union, Optional, Generator
from random import randint as ra
from confluent_kafka import Producer, Consumer, KafkaException


class KafkaProducerWrapper:
    """Kafka Producer (ваш оригинальный код с небольшими улучшениями)"""

    buffer_error_counter: int = 0
    failed: int = 0
    success: int = 0
    buffer_error_retry: int = 2
    conf: Dict
    send_message = None

    def __init__(self, topic: str, bootstrap_servers: str, extra_conf: Dict = None):
        """
        :param topic: str topic name
        :param bootstrap_servers: str addr to kafka server
        :param extra_conf: дополнительные настройки
        """
        self.topic = topic
        self.conf = {
            'client.id': os.getlogin(),
            'bootstrap.servers': str(bootstrap_servers),
            'message.max.bytes': 13631488,  # max sending bytes value
            'receive.message.max.bytes': 13631488 + 1024
        }
        if extra_conf is not None:
            self.conf |= extra_conf

        self.producer = self.__create_producer__()

    def __create_producer__(self) -> Producer:
        """https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md"""
        try:
            return Producer(self.conf)
        except Exception as ex_:
            logger.error(f'Can\'t create Producer cause: \n{ex_}')
            raise

    def get_config(self) -> str:
        """Возвращает конфигурацию в виде JSON строки"""
        return json.dumps(self.conf, indent=2)

    @staticmethod
    def key_hold() -> bytes:
        """Генерирует ключ для сообщения"""
        tick = 10000
        ra_int = ra(tick, tick * tick)
        return ra_int.to_bytes(4, byteorder='big')

    def acked(self, err, msg):
        """Delivery report handler called on successful or failed delivery of message"""
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
            self.failed += 1
        else:
            logger.debug(f'Message delivered to: [{msg.topic()}:{msg.partition()}]')
            self.success += 1

    def send(self, data: Dict | str, on_retry: bool = None) -> bool:
        """
        Sending message
        :param data: dict of message to send
        :type data: Dict
        :param on_retry: retry flag, do not use, only for local executions
        :type on_retry: bool
        :return: True if successful
        :rtype: bool
        """
        assert isinstance(data, Dict | str)
        assert isinstance(on_retry, Union[None, bool])

        if on_retry:
            logger.warning(f'on_retry: [{on_retry}]')
        logger.trace(f'Producing message: \n{data}')

        try:
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)

            # Produce line (without newline)
            self.producer.produce(
                topic=self.topic,
                value=data,
                key=self.key_hold(),
                on_delivery=self.acked)

        except BufferError:
            logger.error(f'Local producer queue is full ({len(self.producer)} messages awaiting delivery)\n')
            sleep(5)
            self.buffer_error_counter += 1
            logger.trace(f"Retries: [{self.buffer_error_counter}]/[{self.buffer_error_retry}]")

            # exit on to many retries
            if self.buffer_error_counter >= self.buffer_error_retry:
                logger.critical("Buffer error exception received over 3 times...")
                logger.debug(f'Stopped: on [{data}]')
                return False

            self.send(data, on_retry=True)
            self.buffer_error_counter = 0
            return True

        except Exception as ex_:
            logger.critical(f'Stopped: on {data}')
            logger.error(f'Some shit happens: {ex_}')
            return False

        self.producer.poll(0)
        self.producer.flush()
        logger.trace(f'Producing: [ok]')
        return True

    def fake_send(self, message: Dict | str, on_retry: bool = None) -> bool:
        """Тестовый метод для имитации отправки"""
        assert isinstance(message, Dict | str)

        logger.trace('\n\n\t=== | JUST TEST | FAKE SEND | ===')
        if isinstance(message, str):
            logger.trace(f'Producing [{on_retry = }] for:\n[{message}]')
        else:
            logger.trace(f'Producing [{on_retry = }] for:\n[{json.dumps(message, ensure_ascii=False)}]')

        return True

    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику отправки"""
        return {
            "success": self.success,
            "failed": self.failed,
            "buffer_errors": self.buffer_error_counter,
            "total": self.success + self.failed
        }

    def flush(self, timeout: float = 30.0) -> int:
        """Ожидает отправки всех сообщений"""
        return self.producer.flush(timeout)


class KafkaConsumerWrapper:
    """Kafka Consumer (ваш оригинальный код)"""

    def __init__(
            self,
            topic: str,
            bootstrap_servers: str,
            group_id: str = None,
            auto_offset_reset: str = 'earliest',
            pool_timeout: float = 1.0,
            enable_auto_commit: bool = True
    ):
        """
        :param topic: Имя топика, на который подписываемся
        :type topic: str
        :param bootstrap_servers: Адрес кафки
        :type bootstrap_servers: str
        :param group_id: группа под которой считываем топик (default='test-{uuid.uuid4()}')
        :type group_id: str
        :param auto_offset_reset: откуда считываем топик [default('earliest'), 'latest']
        :type auto_offset_reset: str
        :param pool_timeout: периодичность обращения к кафке (default=1.0 sec)
        :type pool_timeout: float
        :param enable_auto_commit: коммитим ли сообщения при вычитывании? (default=True)
        :type enable_auto_commit: bool
        """

        # базовые проверки при создании класса
        assert isinstance(topic, str)
        self.consumer = self.__create_consumer__(bootstrap_servers, group_id, auto_offset_reset, enable_auto_commit)
        self.topic = topic
        self.pool_timeout = pool_timeout

    @staticmethod
    def __create_consumer__(
            bootstrap_servers: str,
            group_id: Optional[str],
            auto_offset_reset: str,
            enable_auto_commit: bool
    ) -> Consumer:
        """Создает и настраивает Kafka Consumer"""
        assert auto_offset_reset in ('earliest', 'latest')
        assert isinstance(group_id, (str, type(None)))
        assert isinstance(bootstrap_servers, str)
        assert isinstance(enable_auto_commit, bool)

        client_id = os.getlogin()
        if group_id is None:
            group_id = f'test-{uuid.uuid4()}'

        config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'client.id': client_id,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': enable_auto_commit
        }
        logger.trace(f'Creating consumer:')
        logger.trace(json.dumps(config, indent=2))

        return Consumer(config)

    def consume(self) -> Generator[Optional[str], None, None]:
        """Генератор для потребления сообщений из топика"""
        logger.trace(f'Subscribing to topic: {self.topic}')
        self.consumer.subscribe([self.topic])

        try:
            while True:
                msg = self.consumer.poll(self.pool_timeout)
                if msg is None:  # если ничего не получаем
                    logger.trace(f'No message received from [{self.topic}]')
                    yield None
                    continue
                if msg.error():  # вывести и вернуть ошибку, если что-то пошло не так
                    logger.error(msg.error())
                    raise KafkaException(msg.error())

                message = msg.value().decode('utf-8')
                logger.trace(f'Получено сообщение из: \n'
                             f' - topic: [{msg.topic()}]\n'
                             f' - partition: [{msg.partition()}]\n'
                             f' - message: [{message}]')
                yield message
                continue
        except KeyboardInterrupt:
            pass  # если закрыть руками
        finally:
            self.close()  # при любой не понятной ситуации - закрыть

    def close(self):
        """Закрытие консумера"""
        logger.trace('Closing consumer...')
        self.consumer.close()

    def get_config(self) -> str:
        """Возвращает конфигурацию consumer'а"""
        config = {
            'topic': self.topic,
            'pool_timeout': self.pool_timeout
        }
        return json.dumps(config, indent=2)


class KafkaManager:
    """
    Менеджер для управления несколькими producers/consumers.
    Не обязателен к использованию - можно работать напрямую с KafkaProducerWrapper/KafkaConsumerWrapper
    """

    def __init__(self, bootstrap_servers: str, default_conf: Dict = None):
        """
        :param bootstrap_servers: адреса Kafka брокеров
        :param default_conf: конфигурация по умолчанию для всех клиентов
        """
        self.bootstrap_servers = bootstrap_servers
        self.default_conf = default_conf or {}
        self.producers: Dict[str, KafkaProducerWrapper] = {}
        self.consumers: Dict[str, KafkaConsumerWrapper] = {}
        logger.info(f"KafkaManager initialized for {bootstrap_servers}")

    def get_producer(
            self,
            topic: str,
            reuse: bool = True,
            extra_conf: Dict = None
    ) -> KafkaProducerWrapper:
        """
        Возвращает producer для топика

        :param topic: имя топика
        :param reuse: использовать существующий producer или создать новый
        :param extra_conf: дополнительные настройки
        :return: KafkaProducerWrapper instance
        """
        if reuse and topic in self.producers:
            logger.debug(f"Reusing existing producer for topic '{topic}'")
            return self.producers[topic]

        # Слияние конфигураций: default_conf + extra_conf
        final_conf = self.default_conf.copy()
        if extra_conf:
            final_conf.update(extra_conf)

        producer = KafkaProducerWrapper(
            topic=topic,
            bootstrap_servers=self.bootstrap_servers,
            extra_conf=final_conf
        )

        if reuse:
            self.producers[topic] = producer

        logger.info(f"Created new producer for topic '{topic}'")
        return producer

    def get_consumer(
            self,
            topic: str,
            group_id: str = None,
            auto_offset_reset: str = 'earliest',
            pool_timeout: float = 1.0,
            enable_auto_commit: bool = True
    ) -> KafkaConsumerWrapper:
        """
        Создает и возвращает consumer для топика

        :param topic: имя топика
        :param group_id: группа consumer'ов
        :param auto_offset_reset: с какой позиции читать
        :param pool_timeout: таймаут опроса
        :param enable_auto_commit: авто-коммит оффсетов
        :return: KafkaConsumerWrapper instance
        """
        # Генерируем уникальный ключ для consumer'а
        consumer_key = f"{topic}_{group_id or 'default'}"

        if consumer_key in self.consumers:
            logger.debug(f"Reusing existing consumer for topic '{topic}', group '{group_id}'")
            return self.consumers[consumer_key]

        consumer = KafkaConsumerWrapper(
            topic=topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            pool_timeout=pool_timeout,
            enable_auto_commit=enable_auto_commit
        )

        self.consumers[consumer_key] = consumer
        logger.info(f"Created new consumer for topic '{topic}', group '{group_id}'")
        return consumer

    def send_message(
            self,
            topic: str,
            data: Dict | str,
            reuse_producer: bool = True
    ) -> bool:
        """
        Упрощенная отправка сообщения через менеджер

        :param topic: топик назначения
        :param data: данные для отправки
        :param reuse_producer: использовать переиспользуемый producer
        :return: результат отправки
        """
        producer = self.get_producer(topic, reuse=reuse_producer)
        return producer.send(data)

    def close_all(self):
        """Закрывает все producers и consumers"""
        logger.info("Closing all Kafka clients...")

        # Закрываем producers
        for topic, producer in self.producers.items():
            try:
                producer.flush(5.0)  # Даем время на отправку оставшихся сообщений
                logger.debug(f"Producer for topic '{topic}' flushed")
            except Exception as e:
                logger.error(f"Error flushing producer for topic '{topic}': {e}")

        # Закрываем consumers
        for key, consumer in self.consumers.items():
            try:
                consumer.close()
                logger.debug(f"Consumer '{key}' closed")
            except Exception as e:
                logger.error(f"Error closing consumer '{key}': {e}")

        self.producers.clear()
        self.consumers.clear()
        logger.info("All Kafka clients closed")

    def get_stats(self) -> Dict:
        """Возвращает статистику по всем клиентам"""
        producer_stats = {}
        for topic, producer in self.producers.items():
            producer_stats[topic] = producer.get_stats()

        return {
            "bootstrap_servers": self.bootstrap_servers,
            "producers_count": len(self.producers),
            "consumers_count": len(self.consumers),
            "producers": producer_stats
        }

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из контекста"""
        self.close_all()


# Создание глобального менеджера (опционально)
_default_manager: Optional[KafkaManager] = None


def get_default_manager(bootstrap_servers: str = None) -> KafkaManager:
    """
    Возвращает глобальный менеджер (singleton)

    :param bootstrap_servers: если не указан, нужно создать менеджер вручную
    :return: KafkaManager instance
    """
    global _default_manager
    if _default_manager is None and bootstrap_servers:
        _default_manager = KafkaManager(bootstrap_servers)
    return _default_manager