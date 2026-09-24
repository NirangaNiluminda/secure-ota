"""Unit tests for the verification rules.

One test class per rule, mirroring one row per rule in the threat model. Each
rule is exercised in complete isolation — no registry, no network, no files.
"""

from __future__ import annotations

import pytest

from secure_ota_device.application.policies import (
    IntegrityRule,
    ModelMatchRule,
    RevocationRule,
    RollbackRule,
    VerificationContext,
    VerificationPolicy,
    VerificationStage,
    default_policy,
)
from secure_ota_device.domain import (
    DeviceModel,
    DeviceState,
    FirmwareHash,
    FirmwareImage,
    FirmwareVersion,
    RejectionReason,
)

from ..fakes import MODEL, make_release


def state_at(semver: str | None, model: DeviceModel = MODEL) -> DeviceState:
    return DeviceState(
        model=model,
        installed_version=(
            FirmwareVersion.from_semver(semver)
            if semver
            else FirmwareVersion.UNPROVISIONED
        ),
    )


class TestIntegrityRule:
    def test_accepts_image_matching_the_ledger(self) -> None:
        payload = b"GOOD-FIRMWARE"
        context = VerificationContext(
            state=state_at("1.2.0"),
            release=make_release("1.4.0", payload),
            image=FirmwareImage(payload=payload, source="cdn"),
        )
        assert IntegrityRule().evaluate(context).accepted

    def test_rejects_a_tampered_image(self) -> None:
        context = VerificationContext(
            state=state_at("1.2.0"),
            release=make_release("1.4.0", b"GOOD-FIRMWARE"),
            image=FirmwareImage(payload=b"EVIL-IMPLANT", source="cdn"),
        )
        verdict = IntegrityRule().evaluate(context)
        assert verdict.rejected
        assert verdict.reason is RejectionReason.HASH_MISMATCH

    def test_a_single_flipped_byte_is_enough(self) -> None:
        payload = b"GOOD-FIRMWARE-PAYLOAD"
        context = VerificationContext(
            state=state_at("1.2.0"),
            release=make_release("1.4.0", payload),
            image=FirmwareImage(payload=payload[:-1] + b"X", source="cdn"),
        )
        assert IntegrityRule().evaluate(context).rejected

    def test_fails_closed_when_no_image_was_supplied(self) -> None:
        """A pipeline bug must not become an accepted update."""
        context = VerificationContext(
            state=state_at("1.2.0"), release=make_release("1.4.0"), image=None
        )
        assert IntegrityRule().evaluate(context).rejected


class TestRollbackRule:
    def test_accepts_a_newer_release(self) -> None:
        context = VerificationContext(state_at("1.2.0"), make_release("1.4.0"))
        assert RollbackRule().evaluate(context).accepted

    def test_blocks_an_older_release(self) -> None:
        context = VerificationContext(state_at("1.4.0"), make_release("1.2.0"))
        verdict = RollbackRule().evaluate(context)
        assert verdict.rejected
        assert verdict.reason is RejectionReason.ROLLBACK_BLOCKED
        assert verdict.reason.is_attack_indicator

    def test_reports_the_same_version_as_routine_not_as_an_attack(self) -> None:
        context = VerificationContext(state_at("1.4.0"), make_release("1.4.0"))
        verdict = RollbackRule().evaluate(context)
        assert verdict.reason is RejectionReason.ALREADY_CURRENT
        assert not verdict.reason.is_attack_indicator

    def test_a_factory_fresh_device_accepts_any_release(self) -> None:
        context = VerificationContext(state_at(None), make_release("1.2.0"))
        assert RollbackRule().evaluate(context).accepted


class TestRevocationRule:
    def test_accepts_a_live_release(self) -> None:
        context = VerificationContext(state_at("1.2.0"), make_release("1.4.0"))
        assert RevocationRule().evaluate(context).accepted

    def test_rejects_a_revoked_release(self) -> None:
        context = VerificationContext(
            state_at("1.2.0"), make_release("1.3.0", revoked=True)
        )
        verdict = RevocationRule().evaluate(context)
        assert verdict.rejected
        assert verdict.reason is RejectionReason.RELEASE_REVOKED


class TestModelMatchRule:
    def test_accepts_matching_model(self) -> None:
        context = VerificationContext(state_at("1.2.0"), make_release("1.4.0"))
        assert ModelMatchRule().evaluate(context).accepted

    def test_rejects_firmware_built_for_other_hardware(self) -> None:
        context = VerificationContext(
            state_at("1.2.0"),
            make_release("1.4.0", model=DeviceModel("RUH-GATEWAY-99")),
        )
        verdict = ModelMatchRule().evaluate(context)
        assert verdict.rejected
        assert verdict.reason is RejectionReason.MODEL_MISMATCH


class TestVerificationPolicy:
    def test_refuses_to_be_constructed_empty(self) -> None:
        """An empty policy would accept everything — that must be impossible."""
        with pytest.raises(ValueError, match="at least one rule"):
            VerificationPolicy([])

    def test_short_circuits_at_the_first_rejection(self) -> None:
        """A revoked *and* rolled-back release reports the first rule to refuse."""
        policy = default_policy()
        context = VerificationContext(
            state_at("1.4.0"), make_release("1.2.0", revoked=True)
        )
        verdict = policy.evaluate(context, VerificationStage.PRE_FETCH)
        assert verdict.reason is RejectionReason.RELEASE_REVOKED

    def test_pre_fetch_stage_never_runs_the_integrity_rule(self) -> None:
        """Metadata checks must not need the bytes."""
        names = {
            rule.name
            for rule in default_policy().rules_for(VerificationStage.PRE_FETCH)
        }
        assert "integrity" not in names
        assert names == {"model-match", "revocation", "rollback"}

    def test_integrity_is_the_only_post_fetch_rule(self) -> None:
        rules = default_policy().rules_for(VerificationStage.POST_FETCH)
        assert [rule.name for rule in rules] == ["integrity"]

    def test_every_rule_declares_the_attack_it_defends_against(self) -> None:
        for name, defends in default_policy().describe_defences():
            assert defends.strip(), f"rule {name} does not state its purpose"

    def test_a_clean_release_passes_both_stages(self) -> None:
        payload = b"GOOD-FIRMWARE"
        policy = default_policy()
        context = VerificationContext(
            state=state_at("1.2.0"),
            release=make_release("1.4.0", payload),
            image=FirmwareImage(payload=payload, source="cdn"),
        )
        assert policy.evaluate(context, VerificationStage.PRE_FETCH).accepted
        assert policy.evaluate(context, VerificationStage.POST_FETCH).accepted


class TestFirmwareHashInRules:
    def test_ledger_digest_drives_the_decision_not_the_image(self) -> None:
        """Pin the trust direction: the ledger is authoritative, the bytes are not."""
        payload = b"EVIL"
        release = make_release(
            "1.4.0", firmware_hash=FirmwareHash.of_payload(b"GOOD"), payload=b"GOOD"
        )
        context = VerificationContext(
            state=state_at("1.2.0"),
            release=release,
            image=FirmwareImage(payload=payload, source="attacker"),
        )
        assert IntegrityRule().evaluate(context).rejected
