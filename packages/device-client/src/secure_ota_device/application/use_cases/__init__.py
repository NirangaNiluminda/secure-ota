"""Use cases — the application's interactions, one class each."""

from .inspect_device import DeviceSnapshot, InspectDeviceUseCase
from .report import UpdateOutcome, UpdateReport
from .update_firmware import UpdateFirmwareUseCase

__all__ = [
    "DeviceSnapshot",
    "InspectDeviceUseCase",
    "UpdateFirmwareUseCase",
    "UpdateOutcome",
    "UpdateReport",
]
