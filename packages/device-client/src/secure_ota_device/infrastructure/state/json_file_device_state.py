"""Adapter: device state persisted as a JSON file.

On production hardware the installed version belongs in a protected partition,
an eFuse counter or a secure element — an attacker who can rewrite it to ``0``
defeats rollback protection entirely. The file here is the demo stand-in, and
that limitation is stated openly in the slide deck rather than glossed over.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ...application.ports import DeviceStateRepositoryPort
from ...domain import DeviceModel, DeviceState, DeviceStateCorrupt, FirmwareVersion


class JsonFileDeviceStateRepository(DeviceStateRepositoryPort):
    """Loads and stores :class:`DeviceState` as JSON."""

    def __init__(self, path: Path, default_model: DeviceModel) -> None:
        self._path = path
        self._default_model = default_model

    def load(self) -> DeviceState:
        if not self._path.exists():
            return DeviceState.factory_fresh(self._default_model)

        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
            return DeviceState(
                model=DeviceModel(document["model"]),
                installed_version=FirmwareVersion(int(document["installedVersion"])),
            )
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            raise DeviceStateCorrupt(f"{self._path}: {exc}") from exc

    def save(self, state: DeviceState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "model": str(state.model),
            "installedVersion": state.installed_version.code,
            "installedSemver": state.installed_version.semver,
            "lastCheckedAt": (
                state.last_checked_at.isoformat() if state.last_checked_at else None
            ),
        }

        # Atomic replace: a power cut during an update must not corrupt the
        # record of what the device is running.
        temporary = self._path.with_suffix(".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self._path)
