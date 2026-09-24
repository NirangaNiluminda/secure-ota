"""Read-only use case: report what the device is running and what it defends.

Backs ``secure-ota-device status``. Kept separate from the update cycle because
it must never mutate state — useful during the demo to show the device's posture
before and after each attack without perturbing it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...domain import DeviceModel, FirmwareVersion, Release
from ..policies import VerificationPolicy
from ..ports import DeviceStateRepositoryPort, ReleaseRegistryPort


@dataclass(frozen=True, slots=True)
class DeviceSnapshot:
    """What the device knows about itself right now."""

    model: DeviceModel
    installed_version: FirmwareVersion
    registry_source: str
    latest_release: Release | None
    defences: list[tuple[str, str]]
    registry_error: str | None = None

    @property
    def update_available(self) -> bool:
        return (
            self.latest_release is not None
            and self.latest_release.version > self.installed_version
            and not self.latest_release.revoked
        )


class InspectDeviceUseCase:
    """Assembles a :class:`DeviceSnapshot` without changing anything."""

    def __init__(
        self,
        registry: ReleaseRegistryPort,
        state_repository: DeviceStateRepositoryPort,
        policy: VerificationPolicy,
    ) -> None:
        self._registry = registry
        self._state = state_repository
        self._policy = policy

    def execute(self) -> DeviceSnapshot:
        state = self._state.load()

        latest: Release | None = None
        error: str | None = None
        try:
            latest = self._registry.latest_release(state.model)
        except Exception as exc:  # noqa: BLE001 - status must never crash
            error = str(exc)

        return DeviceSnapshot(
            model=state.model,
            installed_version=state.installed_version,
            registry_source=self._registry.describe_source(),
            latest_release=latest,
            defences=self._policy.describe_defences(),
            registry_error=error,
        )
