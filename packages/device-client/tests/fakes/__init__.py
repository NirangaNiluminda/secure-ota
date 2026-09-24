"""In-memory test doubles for every port.

Because each is a real implementation of the port ABC, the use case under test
is the production object with production wiring — only the edges are swapped.
No mocking framework, no patching, and nothing in the application layer has to
be written differently to be testable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from secure_ota_device.application.ports import (
    DeviceEvent,
    DeviceStateRepositoryPort,
    EventKind,
    EventSinkPort,
    FirmwareInstallerPort,
    FirmwareStorePort,
    ReleaseRegistryPort,
)
from secure_ota_device.domain import (
    DeviceModel,
    DeviceState,
    FirmwareFetchFailed,
    FirmwareHash,
    FirmwareImage,
    FirmwareVersion,
    InstallationFailed,
    RegistryUnavailable,
    Release,
)

MODEL = DeviceModel("RUH-SENSOR-01")


def make_release(
    semver: str = "1.4.0",
    payload: bytes = b"GOOD-FIRMWARE-PAYLOAD",
    *,
    revoked: bool = False,
    model: DeviceModel = MODEL,
    locator: str = "http://vendor.example/fw.bin",
    firmware_hash: FirmwareHash | None = None,
) -> Release:
    """Build a release whose digest matches ``payload`` unless overridden."""
    return Release(
        model=model,
        version=FirmwareVersion.from_semver(semver),
        firmware_hash=firmware_hash or FirmwareHash.of_payload(payload),
        locator=locator,
        published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        revoked=revoked,
    )


class InMemoryReleaseRegistry(ReleaseRegistryPort):
    """A registry backed by a dict."""

    def __init__(self, *releases: Release) -> None:
        self._by_version = {release.version.code: release for release in releases}

    def describe_source(self) -> str:
        return "in-memory registry"

    def latest_release(self, model: DeviceModel) -> Release | None:
        if not self._by_version:
            return None
        return self._by_version[max(self._by_version)]

    def release_at(
        self, model: DeviceModel, version: FirmwareVersion
    ) -> Release | None:
        return self._by_version.get(version.code)


class UnavailableReleaseRegistry(ReleaseRegistryPort):
    """Always raises, to prove the device fails closed."""

    def describe_source(self) -> str:
        return "unreachable registry"

    def latest_release(self, model: DeviceModel) -> Release | None:
        raise RegistryUnavailable("connection refused")

    def release_at(
        self, model: DeviceModel, version: FirmwareVersion
    ) -> Release | None:
        raise RegistryUnavailable("connection refused")


class InMemoryFirmwareStore(FirmwareStorePort):
    """Serves fixed bytes for any locator.

    ``served`` is what the *attacker* delivers, which is not necessarily what
    the ledger promised — the whole point of the integrity test.
    """

    def __init__(self, served: bytes | None = None, *, fail: bool = False) -> None:
        self._served = served
        self._fail = fail
        self.fetch_count = 0

    def supports(self, locator: str) -> bool:
        return True

    def fetch(self, locator: str) -> FirmwareImage:
        self.fetch_count += 1
        if self._fail or self._served is None:
            raise FirmwareFetchFailed(f"simulated fetch failure for {locator}")
        return FirmwareImage(payload=self._served, source=locator)


class RecordingInstaller(FirmwareInstallerPort):
    """Records what it was asked to install; optionally fails."""

    def __init__(self, *, fail: bool = False) -> None:
        self.installed: list[Release] = []
        self._fail = fail

    def describe_target(self) -> str:
        return "recording installer"

    def install(self, image: FirmwareImage, release: Release) -> None:
        if self._fail:
            raise InstallationFailed("simulated flash failure")
        self.installed.append(release)

    @property
    def install_count(self) -> int:
        return len(self.installed)


class InMemoryDeviceStateRepository(DeviceStateRepositoryPort):
    """Holds device state in memory."""

    def __init__(self, state: DeviceState | None = None) -> None:
        self._state = state or DeviceState.factory_fresh(MODEL)
        self.save_count = 0

    def load(self) -> DeviceState:
        return self._state

    def save(self, state: DeviceState) -> None:
        self._state = state
        self.save_count += 1


class CollectingEventSink(EventSinkPort):
    """Captures emitted events for assertions."""

    def __init__(self) -> None:
        self.events: list[DeviceEvent] = []

    def emit(self, event: DeviceEvent) -> None:
        self.events.append(event)

    def kinds(self) -> list[EventKind]:
        return [event.kind for event in self.events]

    def has(self, kind: EventKind) -> bool:
        return any(event.kind is kind for event in self.events)


class ExplodingEventSink(EventSinkPort):
    """Always raises, to prove observability cannot break the device."""

    def emit(self, event: DeviceEvent) -> None:
        raise RuntimeError("sink is broken")
