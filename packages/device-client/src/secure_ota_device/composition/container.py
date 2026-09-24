"""The composition root.

The single place in the codebase where abstractions meet implementations. Every
``new`` of an adapter happens here; everywhere else receives its collaborators
through constructor injection.

That concentration is the property that makes the rest of the design work. To
run the device against a real testnet instead of a fixture file, or to flash
real hardware instead of a simulated slot, you change this file and nothing
else — no use case, no rule, no domain type is aware that a choice was made.
"""

from __future__ import annotations

from functools import cached_property

from ..application.policies import VerificationPolicy, default_policy
from ..application.ports import (
    CompositeEventSink,
    DeviceStateRepositoryPort,
    EventSinkPort,
    FirmwareInstallerPort,
    FirmwareStorePort,
    ReleaseRegistryPort,
)
from ..application.use_cases import InspectDeviceUseCase, UpdateFirmwareUseCase
from ..domain import DeviceModel
from ..infrastructure.blockchain.fixture_release_registry import FixtureReleaseRegistry
from ..infrastructure.installer.simulated_installer import SimulatedSlotInstaller
from ..infrastructure.observability.console_event_sink import (
    AuditLogEventSink,
    ConsoleEventSink,
)
from ..infrastructure.state.json_file_device_state import JsonFileDeviceStateRepository
from ..infrastructure.storage.http_firmware_store import (
    FileFirmwareStore,
    HttpFirmwareStore,
    IpfsGatewayFirmwareStore,
    RoutingFirmwareStore,
)
from .settings import Settings


class DeviceContainer:
    """Builds the device's object graph from :class:`Settings`.

    Adapters are ``cached_property`` so each is constructed at most once and
    only if something actually asks for it — a status check never opens an RPC
    connection it does not need.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # -- primitives ------------------------------------------------------

    @cached_property
    def model(self) -> DeviceModel:
        return DeviceModel(self.settings.model)

    @cached_property
    def policy(self) -> VerificationPolicy:
        return default_policy()

    # -- adapters --------------------------------------------------------

    @cached_property
    def registry(self) -> ReleaseRegistryPort:
        """Chain-backed when a contract address is configured, fixture otherwise.

        The fallback is what let this package be finished and demonstrated
        before the contract existed, and it is the rehearsed safety net if the
        network fails during the live presentation.
        """
        if self.settings.uses_chain:
            from ..infrastructure.blockchain.web3_release_registry import (  # noqa: PLC0415
                Web3ReleaseRegistry,
            )

            return Web3ReleaseRegistry(
                rpc_url=self.settings.rpc_url,
                contract_address=self.settings.contract_address or "",
            )
        return FixtureReleaseRegistry(self.settings.fixture_path)

    @cached_property
    def firmware_store(self) -> FirmwareStorePort:
        return RoutingFirmwareStore(
            IpfsGatewayFirmwareStore(gateway_url=self.settings.ipfs_gateway),
            HttpFirmwareStore(),
            FileFirmwareStore(),
        )

    @cached_property
    def installer(self) -> FirmwareInstallerPort:
        return SimulatedSlotInstaller(self.settings.slot_path)

    @cached_property
    def state_repository(self) -> DeviceStateRepositoryPort:
        return JsonFileDeviceStateRepository(
            path=self.settings.state_path, default_model=self.model
        )

    @cached_property
    def events(self) -> EventSinkPort:
        sinks: list[EventSinkPort] = [ConsoleEventSink()]
        if self.settings.audit_log_path is not None:
            sinks.append(AuditLogEventSink(self.settings.audit_log_path))
        return CompositeEventSink(*sinks)

    # -- use cases -------------------------------------------------------

    @cached_property
    def update_firmware(self) -> UpdateFirmwareUseCase:
        return UpdateFirmwareUseCase(
            registry=self.registry,
            store=self.firmware_store,
            installer=self.installer,
            state_repository=self.state_repository,
            policy=self.policy,
            events=self.events,
        )

    @cached_property
    def inspect_device(self) -> InspectDeviceUseCase:
        return InspectDeviceUseCase(
            registry=self.registry,
            state_repository=self.state_repository,
            policy=self.policy,
        )
