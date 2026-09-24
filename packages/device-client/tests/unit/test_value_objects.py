"""Unit tests for the domain value objects."""

from __future__ import annotations

import pytest

from secure_ota_device.domain import DeviceModel, FirmwareHash, FirmwareVersion
from secure_ota_device.domain.value_objects import (
    InvalidDeviceModel,
    InvalidFirmwareHash,
    InvalidFirmwareVersion,
)


class TestFirmwareHash:
    def test_digest_of_payload_is_sha256(self) -> None:
        import hashlib

        payload = b"firmware-bytes"
        assert (
            FirmwareHash.of_payload(payload).digest == hashlib.sha256(payload).digest()
        )

    def test_hex_round_trip(self) -> None:
        original = FirmwareHash.of_payload(b"abc")
        assert FirmwareHash.from_hex(original.hex).matches(original)

    def test_accepts_hex_with_and_without_prefix(self) -> None:
        bare = "a" * 64
        assert FirmwareHash.from_hex(bare).matches(FirmwareHash.from_hex("0x" + bare))

    def test_differing_payloads_do_not_match(self) -> None:
        assert not FirmwareHash.of_payload(b"good").matches(
            FirmwareHash.of_payload(b"evil")
        )

    @pytest.mark.parametrize("bad", ["", "0x123", "z" * 64, "a" * 63])
    def test_rejects_malformed_hex(self, bad: str) -> None:
        with pytest.raises(InvalidFirmwareHash):
            FirmwareHash.from_hex(bad)

    def test_rejects_wrong_length_digest(self) -> None:
        with pytest.raises(InvalidFirmwareHash):
            FirmwareHash(b"too-short")


class TestFirmwareVersion:
    @pytest.mark.parametrize(
        ("semver", "code"),
        [("0.0.1", 1), ("1.0.0", 10_000), ("1.2.0", 10_200), ("1.4.3", 10_403)],
    )
    def test_semver_encodes_to_monotonic_code(self, semver: str, code: int) -> None:
        assert FirmwareVersion.from_semver(semver).code == code

    def test_semver_round_trip(self) -> None:
        assert FirmwareVersion.from_semver("2.7.9").semver == "2.7.9"

    def test_ordering_follows_release_order(self) -> None:
        versions = [
            FirmwareVersion.from_semver(v) for v in ("1.4.0", "1.2.0", "2.0.0", "1.3.1")
        ]
        assert [v.semver for v in sorted(versions)] == [
            "1.2.0",
            "1.3.1",
            "1.4.0",
            "2.0.0",
        ]

    def test_unprovisioned_sentinel_is_zero_and_sorts_first(self) -> None:
        assert FirmwareVersion.UNPROVISIONED.code == 0
        assert not FirmwareVersion.UNPROVISIONED.is_provisioned
        assert FirmwareVersion.UNPROVISIONED < FirmwareVersion.from_semver("0.0.1")

    @pytest.mark.parametrize("bad", ["", "1.2", "1.2.3.4", "v1.2.3", "1.100.0"])
    def test_rejects_malformed_versions(self, bad: str) -> None:
        with pytest.raises(InvalidFirmwareVersion):
            FirmwareVersion.from_semver(bad)

    def test_rejects_negative_code(self) -> None:
        with pytest.raises(InvalidFirmwareVersion):
            FirmwareVersion(-1)


class TestDeviceModel:
    def test_trims_surrounding_whitespace(self) -> None:
        assert DeviceModel("  RUH-SENSOR-01  ").identifier == "RUH-SENSOR-01"

    def test_compares_by_value(self) -> None:
        assert DeviceModel("A") == DeviceModel("A")
        assert DeviceModel("A") != DeviceModel("B")

    @pytest.mark.parametrize("bad", ["", "   ", "x" * 65])
    def test_rejects_invalid_identifiers(self, bad: str) -> None:
        with pytest.raises(InvalidDeviceModel):
            DeviceModel(bad)
