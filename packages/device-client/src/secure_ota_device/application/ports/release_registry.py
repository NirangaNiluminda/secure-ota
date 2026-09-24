"""Port: the source of truth for what a release *should* be.

Backed by the blockchain in production and by an in-memory fake in tests. The
application layer never learns which, so not one line of use-case or policy code
mentions web3, RPC endpoints or ABIs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain import DeviceModel, FirmwareVersion, Release


class ReleaseRegistryPort(ABC):
    """Read-only view of the on-chain firmware release register."""

    @abstractmethod
    def latest_release(self, model: DeviceModel) -> Release | None:
        """Return the newest published release, or ``None`` if there is none.

        Raises:
            RegistryUnavailable: if the ledger cannot be reached. Callers must
                fail closed rather than treating this as "no update".
        """

    @abstractmethod
    def release_at(
        self, model: DeviceModel, version: FirmwareVersion
    ) -> Release | None:
        """Return a specific historical release, or ``None`` if unknown."""

    @abstractmethod
    def describe_source(self) -> str:
        """Human-readable description of where this data came from.

        Shown in the demo so the audience can see the device is reading a real
        contract at a real address, not a local file.
        """
