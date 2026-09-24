"""Verification verdicts.

A rejected update is an ordinary, expected outcome, not an exceptional one, so
the verification pipeline returns a :class:`Verdict` rather than raising. That
keeps "the device refused a malicious update" on the normal control-flow path
where it can be tested, logged and demonstrated.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RejectionReason(str, Enum):
    """Every way an update can be refused.

    The string values double as the machine-readable codes the event sink emits,
    so the demo output and the test assertions share one vocabulary.
    """

    HASH_MISMATCH = "HASH_MISMATCH"
    ROLLBACK_BLOCKED = "ROLLBACK_BLOCKED"
    RELEASE_REVOKED = "RELEASE_REVOKED"
    MODEL_MISMATCH = "MODEL_MISMATCH"
    ALREADY_CURRENT = "ALREADY_CURRENT"
    NO_RELEASE_PUBLISHED = "NO_RELEASE_PUBLISHED"
    FETCH_FAILED = "FETCH_FAILED"
    REGISTRY_UNREACHABLE = "REGISTRY_UNREACHABLE"

    @property
    def is_attack_indicator(self) -> bool:
        """Whether this rejection suggests tampering rather than routine state.

        Used to decide what deserves a loud warning in the console and what is
        just a device that is already up to date.
        """
        return self in {
            RejectionReason.HASH_MISMATCH,
            RejectionReason.ROLLBACK_BLOCKED,
            RejectionReason.RELEASE_REVOKED,
            RejectionReason.MODEL_MISMATCH,
        }


@dataclass(frozen=True, slots=True)
class Verdict:
    """The result of evaluating one rule, or of an entire policy."""

    accepted: bool
    reason: RejectionReason | None = None
    detail: str = ""
    rule: str = ""

    def __post_init__(self) -> None:
        if self.accepted and self.reason is not None:
            raise ValueError("an accepting verdict cannot carry a rejection reason")
        if not self.accepted and self.reason is None:
            raise ValueError("a rejecting verdict must carry a rejection reason")

    @classmethod
    def accept(cls, rule: str = "") -> "Verdict":
        return cls(accepted=True, rule=rule)

    @classmethod
    def reject(
        cls, reason: RejectionReason, detail: str = "", rule: str = ""
    ) -> "Verdict":
        return cls(accepted=False, reason=reason, detail=detail, rule=rule)

    @property
    def rejected(self) -> bool:
        return not self.accepted

    def __str__(self) -> str:
        if self.accepted:
            return f"accepted by {self.rule or 'policy'}"
        return f"{self.reason.value if self.reason else 'REJECTED'}: {self.detail}"
