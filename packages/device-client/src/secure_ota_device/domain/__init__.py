"""Domain layer — pure business rules, no I/O, no third-party imports.

Everything here is framework-agnostic and instantly unit-testable. The
dependency rule for this codebase: *nothing in ``domain`` may import from
``application``, ``infrastructure``, ``composition`` or ``cli``.*
"""

from .errors import (
    DeviceStateCorrupt,
    FirmwareFetchFailed,
    InstallationFailed,
    RegistryUnavailable,
    SecureOtaError,
)
from .models import DeviceState, FirmwareImage, Release
from .value_objects import DeviceModel, FirmwareHash, FirmwareVersion
from .verdicts import RejectionReason, Verdict

__all__ = [
    "DeviceModel",
    "DeviceState",
    "DeviceStateCorrupt",
    "FirmwareFetchFailed",
    "FirmwareHash",
    "FirmwareImage",
    "FirmwareVersion",
    "InstallationFailed",
    "RegistryUnavailable",
    "RejectionReason",
    "Release",
    "SecureOtaError",
    "Verdict",
]
