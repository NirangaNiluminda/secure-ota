"""Composition of verification rules into a policy.

Composite + Chain of Responsibility: a policy *is a* collection of rules and is
evaluated like a single rule, stopping at the first rejection. Because the
composite satisfies the same contract as its parts, a policy can nest inside
another policy without anything noticing.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from ...domain import Verdict
from .integrity_rule import IntegrityRule
from .model_match_rule import ModelMatchRule
from .revocation_rule import RevocationRule
from .rollback_rule import RollbackRule
from .rule import VerificationContext, VerificationRule, VerificationStage


class VerificationPolicy:
    """An ordered, short-circuiting collection of rules."""

    def __init__(self, rules: Iterable[VerificationRule]) -> None:
        self._rules: tuple[VerificationRule, ...] = tuple(rules)
        if not self._rules:
            # An empty policy would accept everything. Refuse to construct one:
            # a misconfigured device must not silently become an unverified one.
            raise ValueError("a verification policy must contain at least one rule")

    @property
    def rules(self) -> Sequence[VerificationRule]:
        return self._rules

    def rules_for(self, stage: VerificationStage) -> Sequence[VerificationRule]:
        return tuple(rule for rule in self._rules if rule.stage is stage)

    def evaluate(
        self, context: VerificationContext, stage: VerificationStage
    ) -> Verdict:
        """Run every rule registered for ``stage``, stopping at the first refusal.

        The stage is an explicit argument rather than something inferred from
        whether an image is present. Inferring it would mean a pipeline bug
        silently skipped the integrity check — the one failure mode this whole
        project exists to prevent.
        """
        applicable = self.rules_for(stage)
        if not applicable:
            return Verdict.accept(rule=f"{stage.name}:no-rules")

        for rule in applicable:
            verdict = rule.evaluate(context)
            if verdict.rejected:
                return verdict

        return Verdict.accept(rule=f"{stage.name}:all-passed")

    def describe_defences(self) -> list[tuple[str, str]]:
        """``(rule name, attack defended)`` pairs, for the CLI and the slides."""
        return [(rule.name, rule.defends_against) for rule in self._rules]


def default_policy() -> VerificationPolicy:
    """The production rule set.

    Ordering is intentional. Cheap metadata checks come first so a bad update is
    refused before any bandwidth is spent, and the integrity check runs last
    because it is the only one that needs the downloaded bytes.
    """
    return VerificationPolicy(
        [
            ModelMatchRule(),
            RevocationRule(),
            RollbackRule(),
            IntegrityRule(),
        ]
    )
