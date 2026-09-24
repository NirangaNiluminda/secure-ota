"""Adapter: a registry backed by a JSON fixture file.

Not a test double — a first-class offline adapter. It exists so the device
client could be demonstrated, and every attack scenario rehearsed, before the
contract package was deployed anywhere. That is the practical payoff of the port
abstraction: two members were never blocked on each other.

It is also the safety net for the live presentation. If campus Wi-Fi drops or
the testnet RPC rate-limits mid-demo, ``--offline`` reproduces the exact same
verdicts from disk.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ...application.ports import ReleaseRegistryPort
from ...domain import (
    DeviceModel,
    FirmwareHash,
    FirmwareVersion,
    RegistryUnavailable,
    Release,
)


class FixtureReleaseRegistry(ReleaseRegistryPort):
    """Serves releases from a JSON document on disk."""

    def __init__(self, fixture_path: Path) -> None:
        self._path = fixture_path
        self._releases: dict[str, dict[int, Release]] = {}
        self._load()

    def describe_source(self) -> str:
        return f"offline fixture registry ({self._path.name})"

    def latest_release(self, model: DeviceModel) -> Release | None:
        by_version = self._releases.get(model.identifier)
        if not by_version:
            return None
        return by_version[max(by_version)]

    def release_at(
        self, model: DeviceModel, version: FirmwareVersion
    ) -> Release | None:
        return self._releases.get(model.identifier, {}).get(version.code)

    # -- internals -------------------------------------------------------

    def _load(self) -> None:
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryUnavailable(f"cannot read {self._path}: {exc}") from exc

        model_id = document["deviceModel"]
        model = DeviceModel(model_id)
        bucket: dict[int, Release] = {}

        for entry in document["releases"]:
            version = FirmwareVersion(int(entry["version"]))
            # Prefer a declared digest; otherwise derive it from the payload so
            # the fixture cannot drift out of sync with the bytes it describes.
            if entry.get("firmwareHashOverride"):
                digest = FirmwareHash.from_hex(entry["firmwareHashOverride"])
            else:
                digest = FirmwareHash.of_payload(entry["payload"].encode("utf-8"))

            bucket[version.code] = Release(
                model=model,
                version=version,
                firmware_hash=digest,
                locator=self._resolve_locator(entry["locator"]),
                published_at=datetime.fromtimestamp(
                    int(entry.get("publishedAt", 0)), tz=timezone.utc
                ),
                revoked=bool(entry.get("revoked", False)),
            )

        self._releases[model_id] = bucket

    def _resolve_locator(self, locator: str) -> str:
        """Make bare relative locators portable.

        A fixture checked into the repository cannot hard-code absolute paths,
        so a locator with no URL scheme is resolved against the fixture's own
        directory. Anything with a scheme is passed through untouched.
        """
        if "://" in locator:
            return locator
        return str((self._path.parent / locator).resolve())
