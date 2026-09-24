"""The central use case: verify, then maybe install, a firmware update.

This class is the only place that knows the *order* of the update cycle. It
depends on five abstractions and zero concrete implementations, so the same
object runs against a real contract on Sepolia or against in-memory fakes in a
unit test with no change to its code.
"""

from __future__ import annotations

from ...domain import (
    DeviceStateCorrupt,
    FirmwareFetchFailed,
    FirmwareVersion,
    InstallationFailed,
    RegistryUnavailable,
    RejectionReason,
    Release,
    Verdict,
)
from ..policies import VerificationContext, VerificationPolicy, VerificationStage
from ..ports import (
    DeviceEvent,
    DeviceStateRepositoryPort,
    EventKind,
    EventSinkPort,
    FirmwareInstallerPort,
    FirmwareStorePort,
    ReleaseRegistryPort,
)
from .report import UpdateOutcome, UpdateReport


class UpdateFirmwareUseCase:
    """Runs one complete update cycle.

    Collaborators are injected through their ports (constructor injection); the
    composition root decides which adapters they are.
    """

    def __init__(
        self,
        registry: ReleaseRegistryPort,
        store: FirmwareStorePort,
        installer: FirmwareInstallerPort,
        state_repository: DeviceStateRepositoryPort,
        policy: VerificationPolicy,
        events: EventSinkPort,
    ) -> None:
        self._registry = registry
        self._store = store
        self._installer = installer
        self._state = state_repository
        self._policy = policy
        self._events = events

    def execute(
        self,
        *,
        target_version: FirmwareVersion | None = None,
        dry_run: bool = False,
    ) -> UpdateReport:
        """Check for an update and install it if every rule accepts it.

        Args:
            target_version: Pin the cycle to a specific release instead of the
                latest. This is how the attack harness reproduces a downgrade:
                a hostile RPC endpoint or proxy steering the device at an old
                but genuine release.
            dry_run: Verify fully, then stop short of writing to the slot.
        """
        try:
            state = self._state.load()
        except DeviceStateCorrupt as exc:
            return self._fail(
                FirmwareVersion.UNPROVISIONED, f"device state unreadable: {exc}"
            )

        self._emit(
            EventKind.CHECK_STARTED,
            f"{state.model} running {state.installed_version} — "
            f"querying {self._registry.describe_source()}",
        )

        try:
            release = (
                self._registry.release_at(state.model, target_version)
                if target_version is not None
                else self._registry.latest_release(state.model)
            )
        except RegistryUnavailable as exc:
            # Fail closed. An unreachable ledger is never treated as consent to
            # install an unverified image.
            self._emit(
                EventKind.REGISTRY_ERROR,
                f"ledger unreachable, keeping current firmware: {exc}",
                reason=RejectionReason.REGISTRY_UNREACHABLE,
            )
            return self._fail(state.installed_version, str(exc))

        if release is None:
            return UpdateReport(
                outcome=UpdateOutcome.NO_RELEASE,
                version_before=state.installed_version,
                version_after=state.installed_version,
                detail=f"no release published for {state.model}",
            )

        self._emit(
            EventKind.RELEASE_DISCOVERED,
            f"ledger offers {release.version} — expected digest "
            f"{release.firmware_hash.short}",
            context={"locator": release.locator, "revoked": release.revoked},
        )

        context = VerificationContext(state=state, release=release)

        # Phase 1: metadata-only rules, before spending any bandwidth.
        verdict = self._policy.evaluate(context, VerificationStage.PRE_FETCH)
        if verdict.rejected:
            return self._reject(state.installed_version, release, verdict)

        # Phase 2: fetch from the untrusted source, then check the bytes.
        try:
            image = self._store.fetch(release.locator)
        except FirmwareFetchFailed as exc:
            verdict = Verdict.reject(
                RejectionReason.FETCH_FAILED, str(exc), rule="fetch"
            )
            return self._reject(state.installed_version, release, verdict)

        self._emit(
            EventKind.IMAGE_FETCHED,
            f"pulled {image.size_bytes} bytes from {image.source}",
        )

        verdict = self._policy.evaluate(
            context.with_image(image), VerificationStage.POST_FETCH
        )
        if verdict.rejected:
            return self._reject(state.installed_version, release, verdict)

        self._emit(
            EventKind.INTEGRITY_VERIFIED,
            f"digest matches ledger ({image.digest.short}) — image is authentic",
        )

        if dry_run:
            return UpdateReport(
                outcome=UpdateOutcome.VERIFIED_ONLY,
                version_before=state.installed_version,
                version_after=state.installed_version,
                release=release,
                verdict=verdict,
                detail="verified; not installed (dry run)",
            )

        try:
            self._installer.install(image, release)
        except InstallationFailed as exc:
            return self._fail(state.installed_version, f"install failed: {exc}")

        self._state.save(state.with_installed(release.version))

        self._emit(
            EventKind.UPDATE_INSTALLED,
            f"installed {release.version} to {self._installer.describe_target()}",
        )

        return UpdateReport(
            outcome=UpdateOutcome.INSTALLED,
            version_before=state.installed_version,
            version_after=release.version,
            release=release,
            verdict=verdict,
        )

    # -- internals -------------------------------------------------------

    def _reject(
        self, current: FirmwareVersion, release: Release, verdict: Verdict
    ) -> UpdateReport:
        self._emit(
            EventKind.UPDATE_REJECTED,
            f"refused {release.version}: {verdict.detail}",
            reason=verdict.reason,
            context={"rule": verdict.rule},
        )
        return UpdateReport(
            outcome=UpdateOutcome.REJECTED,
            version_before=current,
            version_after=current,
            release=release,
            verdict=verdict,
            detail=verdict.detail,
        )

    def _fail(self, current: FirmwareVersion, detail: str) -> UpdateReport:
        return UpdateReport(
            outcome=UpdateOutcome.ERROR,
            version_before=current,
            version_after=current,
            detail=detail,
        )

    def _emit(
        self,
        kind: EventKind,
        message: str,
        reason: RejectionReason | None = None,
        context: dict | None = None,
    ) -> None:
        self._events.emit(
            DeviceEvent(
                kind=kind, message=message, reason=reason, context=context or {}
            )
        )
