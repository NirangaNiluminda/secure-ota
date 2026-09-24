"""Revocation: refuse a release the manufacturer has withdrawn.

Today a post-release vulnerability produces an advisory email that most fleets
never act on. Here the withdrawal is a ledger state change the device reads and
enforces by itself, with no dependency on the vendor's servers still being up.
"""

from __future__ import annotations

from ...domain import RejectionReason, Verdict
from .rule import VerificationContext, VerificationRule, VerificationStage


class RevocationRule(VerificationRule):
    """Rejects any release flagged as revoked on-chain."""

    name = "revocation"
    stage = VerificationStage.PRE_FETCH

    @property
    def defends_against(self) -> str:
        return "Installing a release withdrawn after a vulnerability was disclosed"

    def evaluate(self, context: VerificationContext) -> Verdict:
        release = context.release
        if release.revoked:
            return Verdict.reject(
                RejectionReason.RELEASE_REVOKED,
                f"{release.version} was revoked by the manufacturer",
                rule=self.name,
            )
        return Verdict.accept(rule=self.name)
