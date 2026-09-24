"""Adapter: a simulated A/B firmware slot on the local filesystem.

Mirrors how real OTA works on an ESP32 or a Yocto target: write into the
inactive slot, keep the previous image for rollback, then switch the pointer.
Swapping this class for one that drives ``esp_ota_write`` is the only change
needed to run the identical verification logic on hardware.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ...application.ports import FirmwareInstallerPort
from ...domain import FirmwareImage, InstallationFailed, Release


class SimulatedSlotInstaller(FirmwareInstallerPort):
    """Writes verified images into a two-slot directory layout."""

    def __init__(self, slot_directory: Path) -> None:
        self._root = slot_directory

    def describe_target(self) -> str:
        return f"firmware slot at {self._root}"

    def install(self, image: FirmwareImage, release: Release) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)

            active = self._root / "active.bin"
            previous = self._root / "previous.bin"
            staging = self._root / "staging.bin"

            # Stage first, so a crash mid-write cannot leave a half-written
            # image in the active slot.
            staging.write_bytes(bytes(image.payload))

            if active.exists():
                os.replace(active, previous)
            os.replace(staging, active)

            manifest = {
                "model": str(release.model),
                "version": release.version.semver,
                "versionCode": release.version.code,
                "firmwareHash": release.firmware_hash.hex,
                "locator": release.locator,
                "sizeBytes": image.size_bytes,
                "installedAt": datetime.now(timezone.utc).isoformat(),
                "verifiedAgainstLedger": True,
            }
            (self._root / "manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            raise InstallationFailed(str(exc)) from exc
