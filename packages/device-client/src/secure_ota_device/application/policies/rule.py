"""The verification rule abstraction (Strategy pattern).

Every security property SecureOTA claims is one small, independently testable
rule in this package. Adding a defence means adding a class here and listing it
in the default policy — no existing code changes. That is the whole point of the
design: the threat model and the code are in one-to-one correspondence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from ...domain import DeviceState, FirmwareImage, Release, Verdict


class VerificationStage(Enum):
    """When a rule can run.

    Splitting the pipeline lets the device reject a bad update *before* spending
    bandwidth on the download. A revoked or rolled-back release is refused after
    two cheap ledger reads; only the hash check needs the bytes.
    """

    #: Decidable from ledger metadata alone, before any download.
    PRE_FETCH = auto()
    #: Requires the downloaded image.
    POST_FETCH = auto()


@dataclass(frozen=True, slots=True)
class VerificationContext:
    """Everything a rule is allowed to look at.

    Passing one frozen context rather than a widening argument list means a new
    rule that needs more information cannot quietly change every other rule's
    signature.
    """

    state: DeviceState
    release: Release
    image: FirmwareImage | None = None

    def with_image(self, image: FirmwareImage) -> "VerificationContext":
        return VerificationContext(state=self.state, release=self.release, image=image)


class VerificationRule(ABC):
    """One security check."""

    #: Stable identifier used in verdicts, logs and test assertions.
    name: str = "unnamed-rule"
    #: The stage this rule belongs to.
    stage: VerificationStage = VerificationStage.PRE_FETCH

    @abstractmethod
    def evaluate(self, context: VerificationContext) -> Verdict:
        """Return an accepting or rejecting verdict. Must not raise."""

    @property
    @abstractmethod
    def defends_against(self) -> str:
        """The attack this rule blocks.

        Required rather than optional so a rule cannot be added without stating
        which row of the threat model it covers. The CLI prints these as the
        device's advertised defences.
        """
