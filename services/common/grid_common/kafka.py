# This project was developed with assistance from AI tools.

"""Kafka producer/consumer helpers using confluent-kafka."""

from __future__ import annotations

import json
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from opentelemetry import trace
from pydantic import BaseModel

from grid_common.settings import KafkaSettings

logger = structlog.get_logger()


def _build_config(settings: KafkaSettings) -> dict[str, Any]:
    """Build confluent-kafka configuration dict from settings."""
    config: dict[str, Any] = {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "security.protocol": settings.kafka_security_protocol,
    }
    if settings.kafka_sasl_mechanism:
        config["sasl.mechanism"] = settings.kafka_sasl_mechanism
    if settings.kafka_sasl_username:
        config["sasl.username"] = settings.kafka_sasl_username
    if settings.kafka_sasl_password:
        config["sasl.password"] = settings.kafka_sasl_password
    return config


def create_producer(settings: KafkaSettings) -> Producer:
    """Create a confluent-kafka Producer."""
    config = _build_config(settings)
    config["linger.ms"] = 5
    config["compression.type"] = "lz4"
    return Producer(config)


def create_consumer(
    settings: KafkaSettings,
    group_id: str | None = None,
    topics: list[str] | None = None,
    auto_offset_reset: str = "latest",
) -> Consumer:
    """Create a confluent-kafka Consumer subscribed to topics."""
    config = _build_config(settings)
    config["group.id"] = group_id or settings.kafka_consumer_group_id
    config["auto.offset.reset"] = auto_offset_reset
    config["enable.auto.commit"] = True

    consumer = Consumer(config)
    if topics:
        consumer.subscribe(topics)
    return consumer


def _inject_trace_headers() -> dict[str, bytes]:
    """Inject current OTel trace context into Kafka headers."""
    headers: dict[str, bytes] = {}
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        headers["traceparent"] = (
            f"00-{format(ctx.trace_id, '032x')}-{format(ctx.span_id, '016x')}-"
            f"{format(ctx.trace_flags, '02x')}"
        ).encode()
    return headers


def publish_event(
    producer: Producer,
    topic: str,
    event: BaseModel,
    key: str | None = None,
) -> None:
    """Serialize a Pydantic model and publish to a Kafka topic with OTel trace headers."""
    headers = _inject_trace_headers()
    value = event.model_dump_json().encode()
    header_list: list[tuple[str, str | bytes | None]] = [(k, v) for k, v in headers.items()]

    def _delivery_callback(err: KafkaError | None, msg: Any) -> None:
        if err:
            logger.error("kafka_delivery_failed", topic=topic, error=str(err))
        else:
            logger.debug("kafka_delivered", topic=msg.topic(), partition=msg.partition())

    producer.produce(
        topic=topic,
        value=value,
        key=key.encode() if key else None,
        headers=header_list,
        callback=_delivery_callback,
    )
    producer.poll(0)


def consume_events(
    consumer: Consumer,
    timeout: float = 1.0,
    max_messages: int = 100,
) -> list[dict[str, Any]]:
    """Poll for messages and return deserialized dicts with metadata."""
    results: list[dict[str, Any]] = []
    msg = consumer.poll(timeout=timeout)
    if msg is None:
        return results
    err = msg.error()
    if err:
        if err.code() == KafkaError._PARTITION_EOF:
            return results
        raise KafkaException(err)

    raw = msg.value()
    if raw is None:
        return results
    raw_headers = msg.headers() or {}
    headers: dict[str, bytes] = {}
    items = raw_headers.items() if isinstance(raw_headers, dict) else raw_headers
    for k, v in items:
        if isinstance(v, bytes):
            headers[k] = v
    value = json.loads(raw.decode())
    value["_topic"] = msg.topic()
    value["_partition"] = msg.partition()
    value["_offset"] = msg.offset()
    if "traceparent" in headers:
        value["_traceparent"] = headers["traceparent"].decode()
    results.append(value)
    return results
