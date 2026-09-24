"""Adapter: colourised console output.

This is the face of the three-minute demo. A rejection has to be unmistakable
from the back of a lecture hall, so attack indicators are printed in red with a
banner while routine events stay quiet.

ANSI codes are emitted directly rather than pulling in a console library: one
less dependency to install on a borrowed machine minutes before presenting.
"""

from __future__ import annotations

import sys
from typing import TextIO

from ...application.ports import DeviceEvent, EventKind, EventSinkPort

_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"

_STYLES: dict[EventKind, tuple[str, str]] = {
    EventKind.CHECK_STARTED: (_CYAN, "·"),
    EventKind.RELEASE_DISCOVERED: (_CYAN, "·"),
    EventKind.IMAGE_FETCHED: (_DIM, "·"),
    EventKind.INTEGRITY_VERIFIED: (_GREEN, "✓"),
    EventKind.UPDATE_INSTALLED: (_GREEN, "✓"),
    EventKind.UPDATE_REJECTED: (_RED, "✗"),
    EventKind.REGISTRY_ERROR: (_YELLOW, "!"),
}


class ConsoleEventSink(EventSinkPort):
    """Prints events for a human audience."""

    def __init__(self, stream: TextIO | None = None, colour: bool | None = None) -> None:
        self._stream = stream or sys.stdout
        self._colour = (
            colour if colour is not None else getattr(self._stream, "isatty", bool)()
        )

    def emit(self, event: DeviceEvent) -> None:
        colour, glyph = _STYLES.get(event.kind, (_DIM, "·"))

        if event.is_attack_indicator:
            self._write("")
            self._write(
                f"{_BOLD}{_RED}  ⚠  UPDATE REJECTED — {event.reason.value}  ⚠{_RESET}"
                if self._colour and event.reason
                else f"  !! UPDATE REJECTED — "
                f"{event.reason.value if event.reason else 'UNKNOWN'} !!"
            )
            self._write(f"     {event.message}")
            self._write("")
            return

        line = f"  {glyph} {event.message}"
        self._write(f"{colour}{line}{_RESET}" if self._colour else line)

    def _write(self, text: str) -> None:
        print(text, file=self._stream, flush=True)


class AuditLogEventSink(EventSinkPort):
    """Appends every event to a JSON Lines file.

    The device's own tamper-evidence trail. Composed alongside the console sink,
    which is exactly why :class:`CompositeEventSink` exists.
    """

    def __init__(self, path) -> None:  # noqa: ANN001 - pathlib.Path, kept loose for reuse
        self._path = path

    def emit(self, event: DeviceEvent) -> None:
        import json  # noqa: PLC0415 - only needed on the logging path

        self._path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "at": event.at.isoformat(),
            "kind": event.kind.value,
            "message": event.message,
            "reason": event.reason.value if event.reason else None,
            "context": event.context,
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
