"""Rollback prevention: never move backwards to an older firmware.

Defeats the attack a plain signature check cannot see. An attacker replays a
genuine, correctly signed, but *superseded* image whose vulnerability is public.
The bytes verify perfectly; only the version ordering exposes it.
"""

from __future__ import annotations

from ...domain import RejectionReason, Verdict
from .rule import VerificationContext, VerificationRule, VerificationStage


class RollbackRule(VerificationRule):
    """Enforces strictly increasing versions on the device side.

    The contract enforces the same invariant when publishing. Checking it here
    too is deliberate defence in depth: the device must stay safe even if it is
    pointed at a forked chain or a malicious RPC endpoint that lies about state.
    """

    name = "rollback"
    stage = VerificationStage.PRE_FETCH

    @property
    def defends_against(self) -> str:
        return "Downgrade to a genuine but known-vulnerable earlier release"

    def evaluate(self, context: VerificationContext) -> Verdict:
        offered = context.release.version
        installed = context.state.installed_version

        if offered < installed:
            return Verdict.reject(
                RejectionReason.ROLLBACK_BLOCKED,
                f"offered {offered} is older than installed {installed}",
                rule=self.name,
            )

        if offered == installed:
            return Verdict.reject(
                RejectionReason.ALREADY_CURRENT,
                f"already running {installed}",
                rule=self.name,
            )

        return Verdict.accept(rule=self.name)
