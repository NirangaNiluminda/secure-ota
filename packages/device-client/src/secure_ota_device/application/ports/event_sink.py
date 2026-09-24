"""Port: observability.

Observer pattern. The use case announces what happened; sinks decide what to do
with it — colour it for the demo console, append it to an audit log, or collect
it for assertions in tests. Adding a sink never changes the use case.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ...domain import RejectionReason


class EventKind(str, Enum):
    """Everything worth announcing during an update cycle."""

    CHECK_STARTED = "CHECK_STARTED"
    RELEASE_DISCOVERED = "RELEASE_DISCOVERED"
    IMAGE_FETCHED = "IMAGE_FETCHED"
    INTEGRITY_VERIFIED = "INTEGRITY_VERIFIED"
    UPDATE_INSTALLED = "UPDATE_INSTALLED"
    UPDATE_REJECTED = "UPDATE_REJECTED"
    REGISTRY_ERROR = "REGISTRY_ERROR"


@dataclass(frozen=True, slots=True)
class DeviceEvent:
    """A single announcement from the update pipeline."""

    kind: EventKind
    message: str
    reason: RejectionReason | None = None
    context: dict[str, Any] = field(default_factory=dict)
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_attack_indicator(self) -> bool:
        return self.reason is not None and self.reason.is_attack_indicator


class EventSinkPort(ABC):
    """Receives device events."""

    @abstractmethod
    def emit(self, event: DeviceEvent) -> None:
        """Handle one event. Implementations must never raise."""


class CompositeEventSink(EventSinkPort):
    """Fans one event out to several sinks (Composite pattern).

    Lets the CLI print to the console *and* append to an audit log without the
    use case knowing there is more than one destination. A misbehaving sink is
    isolated so it cannot take down an update cycle.
    """

    def __init__(self, *sinks: EventSinkPort) -> None:
        self._sinks: tuple[EventSinkPort, ...] = sinks

    def emit(self, event: DeviceEvent) -> None:
        for sink in self._sinks:
            try:
                sink.emit(event)
            except Exception:  # noqa: BLE001 - observability must never break the device
                continue
