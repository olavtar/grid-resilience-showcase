# This project was developed with assistance from AI tools.

"""SSE multiplexer — consumes all grid.* Kafka topics and streams to clients."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError

from console_backend.settings import ConsoleBackendSettings

logger = structlog.get_logger()

ALL_TOPICS = [
    "grid.weather.forecast",
    "grid.weather.alerts",
    "grid.assets.risk-scores",
    "grid.cameras.escalate",
    "grid.cameras.frames",
    "grid.cameras.findings",
    "grid.crew.work-orders",
    "grid.crew.dispatch",
    "grid.crew.telemetry",
    "grid.faults.detected",
    "grid.faults.restoration",
    "grid.ami.outages",
    "grid.customer.impact",
    "grid.ops.events",
]


class EventMultiplexer:
    """Consumes all Kafka topics in a background thread and fans out to SSE clients."""

    def __init__(self, settings: ConsoleBackendSettings) -> None:
        self._settings = settings
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new SSE client and return its event queue."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s is not q]

    def _broadcast(self, event: dict[str, Any]) -> None:
        with self._lock:
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def _consume_loop(self) -> None:
        consumer = Consumer(
            {
                "bootstrap.servers": self._settings.kafka_bootstrap_servers,
                "group.id": f"{self._settings.kafka_consumer_group_id}-sse",
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            }
        )
        consumer.subscribe(ALL_TOPICS)
        logger.info("sse_consumer_started", topics=len(ALL_TOPICS))

        try:
            while True:
                msg = consumer.poll(timeout=0.5)
                if msg is None:
                    continue
                err = msg.error()
                if err:
                    if err.code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.warning("sse_consumer_error", error=str(err))
                    continue

                raw = msg.value()
                if raw is None:
                    continue
                try:
                    data = json.loads(raw.decode())
                    event = {
                        "topic": msg.topic(),
                        "data": data,
                    }
                    self._broadcast(event)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        finally:
            consumer.close()


async def event_stream(mux: EventMultiplexer) -> AsyncGenerator[dict[str, str], None]:
    """Async generator yielding SSE events from the multiplexer."""
    q = mux.subscribe()
    yield {"event": "connected", "data": "{}"}
    try:
        while True:
            event = await q.get()
            yield {
                "event": event["topic"],
                "data": json.dumps(event["data"]),
            }
    finally:
        mux.unsubscribe(q)
