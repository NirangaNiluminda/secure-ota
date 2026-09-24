"""Model targeting: refuse firmware built for different hardware.

Guards against a cross-model swap — serving a valid, current, correctly hashed
image that simply belongs to another product line. On real hardware, flashing it
bricks the device, which makes this a denial-of-service vector as much as a
correctness one.
"""

from __future__ import annotations

from ...domain import RejectionReason, Verdict
from .rule import VerificationContext, VerificationRule, VerificationStage


class ModelMatchRule(VerificationRule):
    """Rejects a release whose target model is not this device's model."""

    name = "model-match"
    stage = VerificationStage.PRE_FETCH

    @property
    def defends_against(self) -> str:
        return "Cross-model firmware swap that would brick the device"

    def evaluate(self, context: VerificationContext) -> Verdict:
        expected = context.state.model
        offered = context.release.model

        if offered != expected:
            return Verdict.reject(
                RejectionReason.MODEL_MISMATCH,
                f"release targets {offered} but this device is {expected}",
                rule=self.name,
            )
        return Verdict.accept(rule=self.name)
