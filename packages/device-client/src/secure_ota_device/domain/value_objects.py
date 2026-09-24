"""Immutable value objects for the SecureOTA domain.

Nothing in this module imports from any other layer. Value objects are compared
by value, validate themselves on construction, and cannot be mutated afterwards,
so an invalid ``FirmwareHash`` or ``FirmwareVersion`` cannot exist anywhere in
the system.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import ClassVar

_HEX64 = re.compile(r"\A(?:0x)?[0-9a-fA-F]{64}\Z")
_SEMVER = re.compile(r"\A(\d+)\.(\d+)\.(\d+)\Z")

#: Encoding base for semantic versions. ``1.4.0`` becomes ``10400``, which keeps
#: the on-chain ``uint256`` monotonic while staying human-readable in logs.
_MINOR_SCALE = 100
_MAJOR_SCALE = 10_000


class InvalidFirmwareHash(ValueError):
    """Raised when a digest is not a well-formed 32-byte SHA-256 value."""


class InvalidFirmwareVersion(ValueError):
    """Raised when a version cannot be represented on-chain."""


class InvalidDeviceModel(ValueError):
    """Raised when a device model identifier is empty or malformed."""


@dataclass(frozen=True, slots=True)
class FirmwareHash:
    """A SHA-256 digest of a firmware binary, held as raw bytes."""

    digest: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.digest, bytes) or len(self.digest) != 32:
            raise InvalidFirmwareHash("a firmware hash must be exactly 32 bytes")

    @classmethod
    def of_payload(cls, payload: bytes) -> "FirmwareHash":
        """Compute the digest of firmware bytes."""
        return cls(hashlib.sha256(payload).digest())

    @classmethod
    def from_hex(cls, value: str) -> "FirmwareHash":
        """Parse a ``0x``-prefixed or bare 64-character hex string."""
        if not _HEX64.match(value or ""):
            raise InvalidFirmwareHash(f"not a 32-byte hex digest: {value!r}")
        return cls(bytes.fromhex(value[2:] if value.startswith("0x") else value))

    @property
    def hex(self) -> str:
        return "0x" + self.digest.hex()

    @property
    def short(self) -> str:
        """An abbreviated form for console output."""
        full = self.digest.hex()
        return f"0x{full[:8]}…{full[-6:]}"

    def matches(self, other: "FirmwareHash") -> bool:
        """Constant-time comparison.

        Digests here are public, so timing leakage is not a real threat, but an
        integrity check is exactly the place where a habit of constant-time
        comparison belongs.
        """
        return hmac.compare_digest(self.digest, other.digest)

    def __str__(self) -> str:
        return self.hex


@dataclass(frozen=True, slots=True, order=True)
class FirmwareVersion:
    """A release version, stored as the monotonic integer the contract uses."""

    code: int

    #: Sentinel meaning "this device has never been provisioned". Declared as a
    #: ClassVar so ``@dataclass`` does not mistake it for a second field, and
    #: bound below the class body once the slotted class object exists.
    UNPROVISIONED: ClassVar["FirmwareVersion"]

    def __post_init__(self) -> None:
        if not isinstance(self.code, int) or isinstance(self.code, bool):
            raise InvalidFirmwareVersion("version code must be an integer")
        if self.code < 0:
            raise InvalidFirmwareVersion("version code cannot be negative")

    @classmethod
    def from_semver(cls, value: str) -> "FirmwareVersion":
        """Build from a ``major.minor.patch`` string."""
        match = _SEMVER.match(value or "")
        if match is None:
            raise InvalidFirmwareVersion(f"not a semantic version: {value!r}")
        major, minor, patch = (int(part) for part in match.groups())
        if minor >= _MINOR_SCALE or patch >= _MINOR_SCALE:
            raise InvalidFirmwareVersion(
                "minor and patch components must each be below 100"
            )
        return cls(major * _MAJOR_SCALE + minor * _MINOR_SCALE + patch)

    @property
    def semver(self) -> str:
        major, remainder = divmod(self.code, _MAJOR_SCALE)
        minor, patch = divmod(remainder, _MINOR_SCALE)
        return f"{major}.{minor}.{patch}"

    @property
    def is_provisioned(self) -> bool:
        """``False`` only for the zero sentinel used by a factory-fresh device."""
        return self.code > 0

    def __str__(self) -> str:
        return "unprovisioned" if self.code == 0 else f"v{self.semver}"


# Bound after the class body: ``slots=True`` makes @dataclass build a new class
# object, so the sentinel has to be attached to the final one.
FirmwareVersion.UNPROVISIONED = FirmwareVersion(0)


@dataclass(frozen=True, slots=True)
class DeviceModel:
    """Identifies a hardware model; the partition key of the on-chain registry."""

    identifier: str

    def __post_init__(self) -> None:
        cleaned = (self.identifier or "").strip()
        if not cleaned:
            raise InvalidDeviceModel("device model must not be empty")
        if len(cleaned) > 64:
            raise InvalidDeviceModel("device model must be 64 characters or fewer")
        object.__setattr__(self, "identifier", cleaned)

    def __str__(self) -> str:
        return self.identifier
