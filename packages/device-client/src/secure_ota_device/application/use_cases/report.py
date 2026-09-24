"""The result type returned by the update use case.

A report, not an exception and not a bare bool. The CLI renders it, the tests
assert on it, and the attack harness diffs it between scenarios — all from one
structure, so "what the device decided" has exactly one representation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ...domain import FirmwareVersion, Release, Verdict


class UpdateOutcome(str, Enum):
    """The five ways an update cycle can end."""

    INSTALLED = "INSTALLED"
    #: Passed every rule but was not written, because this was a dry run.
    VERIFIED_ONLY = "VERIFIED_ONLY"
    #: A rule refused it. ``verdict.reason`` says which and why.
    REJECTED = "REJECTED"
    #: Nothing published for this model yet.
    NO_RELEASE = "NO_RELEASE"
    #: The ledger or the installer could not be reached; device fails closed.
    ERROR = "ERROR"

    @property
    def is_success(self) -> bool:
        return self in {UpdateOutcome.INSTALLED, UpdateOutcome.VERIFIED_ONLY}


@dataclass(frozen=True, slots=True)
class UpdateReport:
    """A complete account of one update cycle."""

    outcome: UpdateOutcome
    version_before: FirmwareVersion
    version_after: FirmwareVersion
    release: Release | None = None
    verdict: Verdict | None = None
    detail: str = ""

    @property
    def changed_firmware(self) -> bool:
        return self.version_before != self.version_after

    @property
    def is_attack_indicator(self) -> bool:
        """Whether this cycle looks like an attack rather than routine state."""
        return (
            self.verdict is not None
            and self.verdict.reason is not None
            and self.verdict.reason.is_attack_indicator
        )

    @property
    def exit_code(self) -> int:
        """Process exit status, so shell scripts and CI can gate on the result.

        ``0`` success, ``1`` refused, ``2`` could not decide.
        """
        if self.outcome.is_success or self.outcome is UpdateOutcome.NO_RELEASE:
            return 0
        return 1 if self.outcome is UpdateOutcome.REJECTED else 2
