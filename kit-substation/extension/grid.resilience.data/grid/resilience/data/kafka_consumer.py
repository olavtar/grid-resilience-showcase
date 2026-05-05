# This project was developed with assistance from AI tools.

"""Kafka consumer for grid events — queues scene updates for the main thread."""

from __future__ import annotations

import json
import queue

from confluent_kafka import Consumer, KafkaError

TOPICS = [
    "grid.assets.risk-scores",
    "grid.ops.events",
    "grid.faults.detected",
    "grid.faults.restoration",
]


def consume_grid_events(
    bootstrap_servers: str,
    group_id: str,
    update_queue: queue.Queue,
) -> None:
    """Consume grid events from Kafka and queue scene updates."""
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe(TOPICS)

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"[kit-ext] Kafka error: {msg.error()}")
                continue

            try:
                topic = msg.topic()
                data = json.loads(msg.value().decode())
                update_queue.put({"topic": topic, "data": data})
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    finally:
        consumer.close()
