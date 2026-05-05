# This project was developed with assistance from AI tools.

"""Scenario state management."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Beat(StrEnum):
    IDLE = "idle"
    FORECAST = "forecast"
    TRIAGE = "triage"
    ESCALATE = "escalate"
    DISPATCH = "dispatch"
    STORM = "storm"
    RESTORE = "restore"
    TRACE = "trace"


@dataclass
class ScenarioState:
    """Tracks current state of the running scenario."""

    scenario_id: str | None = None
    scenario_name: str | None = None
    current_beat: Beat = Beat.IDLE
    beat_index: int = -1
    is_running: bool = False
    storm_triggered: bool = False
    fault_triggered: bool = False
    events_emitted: int = 0
    scenario_config: dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        self.scenario_id = None
        self.scenario_name = None
        self.current_beat = Beat.IDLE
        self.beat_index = -1
        self.is_running = False
        self.storm_triggered = False
        self.fault_triggered = False
        self.events_emitted = 0
        self.scenario_config = {}

    def advance(self) -> Beat:
        beats = [b for b in Beat if b != Beat.IDLE]
        self.beat_index = min(self.beat_index + 1, len(beats) - 1)
        self.current_beat = beats[self.beat_index]
        return self.current_beat
