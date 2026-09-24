"""Ports — the abstractions the application layer depends on.

Every one is an ABC with no third-party imports. Infrastructure adapters
implement them; the composition root wires the two together. This is the seam
that keeps the business rules testable without a blockchain, a network or a
device.
"""

from .device_state import DeviceStateRepositoryPort
from .event_sink import CompositeEventSink, DeviceEvent, EventKind, EventSinkPort
from .firmware_installer import FirmwareInstallerPort
from .firmware_store import FirmwareStorePort
from .release_registry import ReleaseRegistryPort

__all__ = [
    "CompositeEventSink",
    "DeviceEvent",
    "DeviceStateRepositoryPort",
    "EventKind",
    "EventSinkPort",
    "FirmwareInstallerPort",
    "FirmwareStorePort",
    "ReleaseRegistryPort",
]
