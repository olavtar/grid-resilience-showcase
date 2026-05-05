# This project was developed with assistance from AI tools.

"""Kit extension consuming Kafka events to update substation scene materials."""

from __future__ import annotations

import os
import queue
import threading

import omni.ext
import omni.kit.app

from .kafka_consumer import consume_grid_events
from .scene_updater import (
    PRIM_MAP,
    apply_fault_state,
    apply_restore_state,
    apply_risk_color,
    remove_all_highlights,
)


class GridResilienceDataExtension(omni.ext.IExt):
    """Kit extension consuming Kafka events to update substation scene materials."""

    def on_startup(self, ext_id: str) -> None:
        self._update_queue: queue.Queue = queue.Queue()
        self._shutdown_event = threading.Event()
        self._triage_active = False
        self._buffered_risks: list[dict] = []

        bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        group_id = os.environ.get("KAFKA_CONSUMER_GROUP_ID", "kit-substation")

        self._consumer_thread = threading.Thread(
            target=consume_grid_events,
            args=(bootstrap, group_id, self._update_queue),
            daemon=True,
        )
        self._consumer_thread.start()

        self._update_sub = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(self._on_update, name="grid.resilience.data.update")
        )

        print(f"[grid.resilience.data] Started — Kafka: {bootstrap}")

    def on_shutdown(self) -> None:
        self._shutdown_event.set()
        if self._update_sub:
            self._update_sub = None
        print("[grid.resilience.data] Shutdown")

    def _on_update(self, event: omni.kit.app.IEvent) -> None:
        """Process queued Kafka events on the main thread."""
        while not self._update_queue.empty():
            try:
                msg = self._update_queue.get_nowait()
            except queue.Empty:
                break

            topic = msg["topic"]
            data = msg["data"]

            if topic == "grid.ops.events":
                title = data.get("title", "")
                if "triage" in title.lower():
                    self._triage_active = True
                    for risk in self._buffered_risks:
                        prim_path = PRIM_MAP.get(risk["asset_id"])
                        if prim_path:
                            apply_risk_color(prim_path, risk["score"])
                    self._buffered_risks.clear()
                elif "reset" in title.lower():
                    self._triage_active = False
                    self._buffered_risks.clear()
                    remove_all_highlights()

            elif topic == "grid.assets.risk-scores":
                asset_id = data.get("asset_id", "")
                score = data.get("composite_score", 0.0)
                if self._triage_active:
                    prim_path = PRIM_MAP.get(asset_id)
                    if prim_path:
                        apply_risk_color(prim_path, score)
                else:
                    if asset_id in PRIM_MAP:
                        self._buffered_risks.append({"asset_id": asset_id, "score": score})

            elif topic == "grid.faults.detected":
                prim_path = PRIM_MAP.get("T-008")
                if prim_path:
                    apply_fault_state(prim_path, faulted=True)

            elif topic == "grid.faults.restoration":
                prim_path = PRIM_MAP.get("T-008")
                if prim_path:
                    apply_restore_state(prim_path)
