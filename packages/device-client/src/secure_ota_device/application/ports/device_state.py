"""Port: persistence of the device's own record of what it is running.

Repository pattern. The installed version is the anchor for rollback detection,
so this is security-relevant state: on real hardware it belongs in a protected
partition or secure element, not a writable file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain import DeviceState


class DeviceStateRepositoryPort(ABC):
    """Loads and stores the device's current firmware state."""

    @abstractmethod
    def load(self) -> DeviceState:
        """Return the persisted state, or a factory-fresh one on first boot.

        Raises:
            DeviceStateCorrupt: if existing state is present but unreadable.
        """

    @abstractmethod
    def save(self, state: DeviceState) -> None:
        """Persist the state atomically."""
