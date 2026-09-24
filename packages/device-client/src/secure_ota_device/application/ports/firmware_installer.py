"""Port: writing a verified image into the device's firmware slot.

Abstracted so the same use case drives a simulated flash on a laptop during the
presentation and a real ``esp_ota_write`` on hardware, with no change above
this line.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain import FirmwareImage, Release


class FirmwareInstallerPort(ABC):
    """Applies a verified firmware image."""

    @abstractmethod
    def install(self, image: FirmwareImage, release: Release) -> None:
        """Write the image to the inactive slot and mark it bootable.

        Only ever called with an image that has already passed every
        verification rule.

        Raises:
            InstallationFailed: if the write did not complete.
        """

    @abstractmethod
    def describe_target(self) -> str:
        """Human-readable description of the install target."""
