"""Core domain entities.

These model the three things the device reasons about: what the ledger claims a
release should be (:class:`Release`), what actually arrived over the wire
(:class:`FirmwareImage`), and what the device is currently running
(:class:`DeviceState`).

The security of the whole system reduces to one question this module makes easy
to ask: does the image I downloaded hash to what the ledger says?
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from .value_objects import DeviceModel, FirmwareHash, FirmwareVersion


@dataclass(frozen=True, slots=True)
class Release:
    """An immutable release record as published on-chain.

    This is a *claim* made by the manufacturer, not a trusted artifact. It is
    only meaningful once an image has been checked against ``firmware_hash``.
    """

    model: DeviceModel
    version: FirmwareVersion
    firmware_hash: FirmwareHash
    locator: str
    published_at: datetime
    revoked: bool = False

    def __post_init__(self) -> None:
        if not self.locator:
            raise ValueError("a release must carry a fetch locator")
        if not self.version.is_provisioned:
            raise ValueError("a published release must have a version of at least 1")

    @property
    def is_installable(self) -> bool:
        """A quick read for human output; the policy layer is authoritative."""
        return not self.revoked


@dataclass(frozen=True, slots=True)
class FirmwareImage:
    """The actual bytes fetched from an untrusted source."""

    payload: bytes
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.payload, (bytes, bytearray)):
            raise TypeError("firmware payload must be bytes")
        if len(self.payload) == 0:
            raise ValueError("refusing to handle an empty firmware image")

    @property
    def digest(self) -> FirmwareHash:
        """The hash of what actually arrived, computed locally every time.

        Deliberately not cached: the value must always be derived from the bytes
        in hand, never carried alongside them where it could drift.
        """
        return FirmwareHash.of_payload(bytes(self.payload))

    @property
    def size_bytes(self) -> int:
        return len(self.payload)


@dataclass(frozen=True, slots=True)
class DeviceState:
    """What this device is running right now."""

    model: DeviceModel
    installed_version: FirmwareVersion
    last_checked_at: datetime | None = None

    @classmethod
    def factory_fresh(cls, model: DeviceModel) -> "DeviceState":
        return cls(model=model, installed_version=FirmwareVersion.UNPROVISIONED)

    def with_installed(self, version: FirmwareVersion) -> "DeviceState":
        """Return a new state reflecting a successful install."""
        return replace(
            self,
            installed_version=version,
            last_checked_at=datetime.now(timezone.utc),
        )

    def checked_now(self) -> "DeviceState":
        return replace(self, last_checked_at=datetime.now(timezone.utc))
