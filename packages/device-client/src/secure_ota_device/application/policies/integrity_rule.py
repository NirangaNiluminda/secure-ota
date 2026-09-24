"""Integrity: do the bytes I received hash to what the ledger says?

This is the rule that defeats a compromised CDN or a network MITM. Everything
else in SecureOTA exists to make this single comparison trustworthy.
"""

from __future__ import annotations

from ...domain import RejectionReason, Verdict
from .rule import VerificationContext, VerificationRule, VerificationStage


class IntegrityRule(VerificationRule):
    """Rejects any image whose SHA-256 differs from the on-chain digest."""

    name = "integrity"
    stage = VerificationStage.POST_FETCH

    @property
    def defends_against(self) -> str:
        return "Tampered binary from a compromised update server, CDN or network path"

    def evaluate(self, context: VerificationContext) -> Verdict:
        image = context.image
        if image is None:
            # A programming error, not an attack: the pipeline ran a POST_FETCH
            # rule without downloading. Fail closed rather than pass by default.
            return Verdict.reject(
                RejectionReason.HASH_MISMATCH,
                "no image was supplied to the integrity rule",
                rule=self.name,
            )

        expected = context.release.firmware_hash
        actual = image.digest

        if not actual.matches(expected):
            return Verdict.reject(
                RejectionReason.HASH_MISMATCH,
                (
                    f"ledger expects {expected.short} but {image.size_bytes} bytes "
                    f"from {image.source} hash to {actual.short}"
                ),
                rule=self.name,
            )

        return Verdict.accept(rule=self.name)
