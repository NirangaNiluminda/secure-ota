"""Adapter: reads the FirmwareRegistry contract over JSON-RPC.

The only file in the device client that imports web3. ``web3`` is imported
lazily inside the constructor so the domain, application and test suites run on
a bare Python install — which also keeps the unit tests honest, since they
physically cannot reach a chain.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...application.ports import ReleaseRegistryPort
from ...domain import (
    DeviceModel,
    FirmwareHash,
    FirmwareVersion,
    RegistryUnavailable,
    Release,
)

#: The frozen ABI lives in packages/shared and is copied in at build time; this
#: local path is the fallback so the client stays runnable on its own.
_DEFAULT_ABI_PATH = Path(__file__).parent / "abi" / "FirmwareRegistry.json"


def load_abi(path: Path | None = None) -> list[dict[str, Any]]:
    """Read the ABI array out of the shared spec file."""
    source = path or _DEFAULT_ABI_PATH
    document = json.loads(source.read_text(encoding="utf-8"))
    # Accept either the annotated spec or a bare ABI array.
    return document["abi"] if isinstance(document, dict) else document


class Web3ReleaseRegistry(ReleaseRegistryPort):
    """Reads releases from the on-chain registry."""

    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        abi_path: Path | None = None,
        request_timeout: float = 15.0,
    ) -> None:
        try:
            from web3 import Web3  # noqa: PLC0415 - optional dependency, by design
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RegistryUnavailable(
                "web3 is not installed; run `pip install -e .[chain]` to talk to "
                "a real network, or use the --offline fixture registry"
            ) from exc

        self._rpc_url = rpc_url
        self._address = Web3.to_checksum_address(contract_address)
        self._web3 = Web3(
            Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": request_timeout})
        )
        self._contract = self._web3.eth.contract(
            address=self._address, abi=load_abi(abi_path)
        )

    def describe_source(self) -> str:
        return f"FirmwareRegistry @ {self._address} via {self._rpc_url}"

    def latest_release(self, model: DeviceModel) -> Release | None:
        try:
            code = self._contract.functions.latestVersion(model.identifier).call()
        except Exception as exc:  # noqa: BLE001 - any RPC failure is unavailability
            raise RegistryUnavailable(f"latestVersion failed: {exc}") from exc

        # Version 0 is the contract's sentinel for "nothing published yet".
        if code == 0:
            return None

        return self._read(model, code)

    def release_at(
        self, model: DeviceModel, version: FirmwareVersion
    ) -> Release | None:
        try:
            return self._read(model, version.code)
        except RegistryUnavailable:
            raise
        except Exception:  # noqa: BLE001 - UnknownRelease revert means "absent"
            return None

    # -- internals -------------------------------------------------------

    def _read(self, model: DeviceModel, version_code: int) -> Release:
        try:
            raw = self._contract.functions.releaseAt(
                model.identifier, version_code
            ).call()
        except Exception as exc:  # noqa: BLE001
            raise RegistryUnavailable(f"releaseAt failed: {exc}") from exc
        return self._to_release(model, raw)

    @staticmethod
    def _to_release(model: DeviceModel, raw: Any) -> Release:
        """Translate the ABI tuple into a domain entity.

        The anti-corruption boundary: web3 types (``HexBytes``, raw ints, epoch
        seconds) stop here and never leak inward.
        """
        version, firmware_hash, locator, published_at, revoked = raw
        return Release(
            model=model,
            version=FirmwareVersion(int(version)),
            firmware_hash=FirmwareHash(bytes(firmware_hash)),
            locator=str(locator),
            published_at=datetime.fromtimestamp(int(published_at), tz=timezone.utc),
            revoked=bool(revoked),
        )
