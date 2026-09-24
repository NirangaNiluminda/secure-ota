"""Configuration for the device client.

One immutable object assembled once at start-up from defaults, environment and
CLI flags, in that order of increasing precedence. Nothing below the composition
root ever reads ``os.environ``, so no use case or rule can develop a hidden
dependency on ambient configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[3]  # packages/device-client
_PACKAGES_ROOT = _PACKAGE_ROOT.parent  # packages/

DEFAULT_MODEL = "RUH-SENSOR-01"


@dataclass(frozen=True, slots=True)
class Settings:
    """Everything the composition root needs to build the object graph."""

    model: str = DEFAULT_MODEL
    rpc_url: str = "http://127.0.0.1:8545"
    contract_address: str | None = None
    ipfs_gateway: str = "https://ipfs.io/ipfs/"

    offline: bool = False
    fixture_path: Path = _PACKAGES_ROOT / "shared" / "fixtures" / "sample-releases.json"

    state_path: Path = _PACKAGE_ROOT / ".device-state" / "state.json"
    slot_path: Path = _PACKAGE_ROOT / "firmware-slot"
    audit_log_path: Path | None = _PACKAGE_ROOT / ".device-state" / "audit.jsonl"

    @classmethod
    def from_environment(cls) -> "Settings":
        """Layer ``SECURE_OTA_*`` environment variables over the defaults."""
        base = cls()
        return replace(
            base,
            model=os.environ.get("SECURE_OTA_MODEL", base.model),
            rpc_url=os.environ.get("SECURE_OTA_RPC_URL", base.rpc_url),
            contract_address=os.environ.get(
                "SECURE_OTA_CONTRACT", base.contract_address
            ),
            ipfs_gateway=os.environ.get("SECURE_OTA_IPFS_GATEWAY", base.ipfs_gateway),
            offline=_flag(os.environ.get("SECURE_OTA_OFFLINE"), base.offline),
            fixture_path=Path(
                os.environ.get("SECURE_OTA_FIXTURE", base.fixture_path)
            ),
            state_path=Path(os.environ.get("SECURE_OTA_STATE", base.state_path)),
            slot_path=Path(os.environ.get("SECURE_OTA_SLOT", base.slot_path)),
        )

    @property
    def uses_chain(self) -> bool:
        """Whether a real contract read is configured and wanted."""
        return not self.offline and bool(self.contract_address)


def _flag(raw: str | None, fallback: bool) -> bool:
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "on"}
