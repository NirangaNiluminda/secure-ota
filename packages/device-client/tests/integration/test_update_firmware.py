"""End-to-end tests of the update use case, driven entirely through fakes.

This is the scenario matrix that backs every claim in the threat-model slide.
Each attack in the presentation has a test here that fails loudly if the defence
ever regresses.
"""

from __future__ import annotations

import pytest

from secure_ota_device.application.policies import default_policy
from secure_ota_device.application.ports import CompositeEventSink, EventKind
from secure_ota_device.application.use_cases import (
    UpdateFirmwareUseCase,
    UpdateOutcome,
)
from secure_ota_device.domain import (
    DeviceModel,
    DeviceState,
    FirmwareVersion,
    RejectionReason,
)

from ..fakes import (
    MODEL,
    CollectingEventSink,
    ExplodingEventSink,
    InMemoryDeviceStateRepository,
    InMemoryFirmwareStore,
    InMemoryReleaseRegistry,
    RecordingInstaller,
    UnavailableReleaseRegistry,
    make_release,
)

GOOD = b"GOOD-FIRMWARE-PAYLOAD"
EVIL = b"EVIL-IMPLANT-PAYLOAD"


def build(
    *,
    registry,
    served: bytes | None = GOOD,
    installed: str | None = "1.2.0",
    installer: RecordingInstaller | None = None,
    events: CollectingEventSink | None = None,
    fetch_fails: bool = False,
):
    """Assemble the use case with fakes and hand back the parts tests assert on."""
    state = InMemoryDeviceStateRepository(
        DeviceState(
            model=MODEL,
            installed_version=(
                FirmwareVersion.from_semver(installed)
                if installed
                else FirmwareVersion.UNPROVISIONED
            ),
        )
    )
    installer = installer or RecordingInstaller()
    events = events or CollectingEventSink()
    store = InMemoryFirmwareStore(served, fail=fetch_fails)

    use_case = UpdateFirmwareUseCase(
        registry=registry,
        store=store,
        installer=installer,
        state_repository=state,
        policy=default_policy(),
        events=events,
    )
    return use_case, installer, state, events, store


class TestHappyPath:
    def test_installs_a_verified_release(self) -> None:
        release = make_release("1.4.0", GOOD)
        use_case, installer, state, events, _ = build(
            registry=InMemoryReleaseRegistry(release)
        )

        report = use_case.execute()

        assert report.outcome is UpdateOutcome.INSTALLED
        assert report.version_after == FirmwareVersion.from_semver("1.4.0")
        assert report.changed_firmware
        assert installer.install_count == 1
        assert state.load().installed_version.semver == "1.4.0"
        assert events.has(EventKind.INTEGRITY_VERIFIED)
        assert events.has(EventKind.UPDATE_INSTALLED)
        assert report.exit_code == 0

    def test_dry_run_verifies_without_installing(self) -> None:
        use_case, installer, state, _, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD))
        )

        report = use_case.execute(dry_run=True)

        assert report.outcome is UpdateOutcome.VERIFIED_ONLY
        assert report.outcome.is_success
        assert installer.install_count == 0
        assert state.load().installed_version.semver == "1.2.0"
        assert state.save_count == 0

    def test_a_factory_fresh_device_provisions_itself(self) -> None:
        use_case, installer, _, _, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD)),
            installed=None,
        )
        assert use_case.execute().outcome is UpdateOutcome.INSTALLED
        assert installer.install_count == 1


class TestTamperedBinary:
    """Attack 1: a compromised CDN or MITM swaps the image."""

    def test_rejects_an_image_that_does_not_match_the_ledger(self) -> None:
        use_case, installer, state, events, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD)),
            served=EVIL,
        )

        report = use_case.execute()

        assert report.outcome is UpdateOutcome.REJECTED
        assert report.verdict is not None
        assert report.verdict.reason is RejectionReason.HASH_MISMATCH
        assert report.is_attack_indicator
        assert installer.install_count == 0, "malicious image must never be installed"
        assert state.load().installed_version.semver == "1.2.0"
        assert state.save_count == 0, "a refused update must not touch device state"
        assert events.has(EventKind.UPDATE_REJECTED)
        assert report.exit_code == 1


class TestRollback:
    """Attack 2: replaying a genuine but superseded release."""

    def test_blocks_a_downgrade(self) -> None:
        old = make_release("1.2.0", GOOD)
        use_case, installer, _, _, store = build(
            registry=InMemoryReleaseRegistry(old), installed="1.4.0"
        )

        report = use_case.execute(target_version=FirmwareVersion.from_semver("1.2.0"))

        assert report.verdict is not None
        assert report.verdict.reason is RejectionReason.ROLLBACK_BLOCKED
        assert installer.install_count == 0

    def test_a_downgrade_is_refused_before_any_bytes_are_fetched(self) -> None:
        """The cheap metadata rules must run first — bandwidth is not spent."""
        use_case, _, _, _, store = build(
            registry=InMemoryReleaseRegistry(make_release("1.2.0", GOOD)),
            installed="1.4.0",
        )

        use_case.execute(target_version=FirmwareVersion.from_semver("1.2.0"))

        assert store.fetch_count == 0

    def test_being_up_to_date_is_not_reported_as_an_attack(self) -> None:
        use_case, installer, _, _, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD)),
            installed="1.4.0",
        )

        report = use_case.execute()

        assert report.verdict is not None
        assert report.verdict.reason is RejectionReason.ALREADY_CURRENT
        assert not report.is_attack_indicator
        assert installer.install_count == 0


class TestRevocation:
    """Attack 3: installing a release withdrawn after a CVE."""

    def test_rejects_a_revoked_release(self) -> None:
        use_case, installer, _, _, store = build(
            registry=InMemoryReleaseRegistry(
                make_release("1.3.0", GOOD, revoked=True)
            )
        )

        report = use_case.execute()

        assert report.verdict is not None
        assert report.verdict.reason is RejectionReason.RELEASE_REVOKED
        assert report.is_attack_indicator
        assert installer.install_count == 0
        assert store.fetch_count == 0, "no need to download something already refused"


class TestCrossModel:
    """Attack 4: firmware for different hardware."""

    def test_rejects_firmware_targeting_another_model(self) -> None:
        use_case, installer, _, _, _ = build(
            registry=InMemoryReleaseRegistry(
                make_release("1.4.0", GOOD, model=DeviceModel("RUH-GATEWAY-99"))
            )
        )

        report = use_case.execute()

        assert report.verdict is not None
        assert report.verdict.reason is RejectionReason.MODEL_MISMATCH
        assert installer.install_count == 0


class TestFailureModes:
    def test_fails_closed_when_the_ledger_is_unreachable(self) -> None:
        """No ledger means no update — never an unverified install."""
        use_case, installer, state, events, _ = build(
            registry=UnavailableReleaseRegistry()
        )

        report = use_case.execute()

        assert report.outcome is UpdateOutcome.ERROR
        assert installer.install_count == 0
        assert state.load().installed_version.semver == "1.2.0"
        assert events.has(EventKind.REGISTRY_ERROR)
        assert report.exit_code == 2

    def test_reports_when_nothing_has_been_published(self) -> None:
        use_case, installer, _, _, _ = build(registry=InMemoryReleaseRegistry())

        report = use_case.execute()

        assert report.outcome is UpdateOutcome.NO_RELEASE
        assert installer.install_count == 0
        assert report.exit_code == 0, "an idle fleet is not a failure"

    def test_a_failed_download_does_not_change_the_device(self) -> None:
        use_case, installer, state, _, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD)),
            fetch_fails=True,
        )

        report = use_case.execute()

        assert report.verdict is not None
        assert report.verdict.reason is RejectionReason.FETCH_FAILED
        assert installer.install_count == 0
        assert state.save_count == 0

    def test_a_failed_flash_leaves_the_recorded_version_untouched(self) -> None:
        use_case, _, state, _, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD)),
            installer=RecordingInstaller(fail=True),
        )

        report = use_case.execute()

        assert report.outcome is UpdateOutcome.ERROR
        assert state.load().installed_version.semver == "1.2.0"
        assert state.save_count == 0


class TestObservability:
    def test_a_broken_event_sink_cannot_stop_an_update(self) -> None:
        """Logging is never allowed to take the device down."""
        events = CompositeEventSink(ExplodingEventSink(), CollectingEventSink())
        use_case, installer, _, _, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD))
        )
        use_case._events = events  # noqa: SLF001 - swapping the port under test

        assert use_case.execute().outcome is UpdateOutcome.INSTALLED
        assert installer.install_count == 1

    @pytest.mark.parametrize(
        ("served", "expected"),
        [(GOOD, EventKind.UPDATE_INSTALLED), (EVIL, EventKind.UPDATE_REJECTED)],
    )
    def test_the_cycle_always_announces_how_it_ended(
        self, served: bytes, expected: EventKind
    ) -> None:
        events = CollectingEventSink()
        use_case, _, _, _, _ = build(
            registry=InMemoryReleaseRegistry(make_release("1.4.0", GOOD)),
            served=served,
            events=events,
        )

        use_case.execute()

        assert events.has(expected)
