"""Firmware retrieval over HTTP(S) and from the local filesystem.

Built on ``urllib`` from the standard library rather than ``requests`` so the
device client has no mandatory third-party dependency for the demo path. On a
constrained target that matters; in a presentation it means the examiners can
run it with a bare Python install.

None of these adapters authenticate anything. That is deliberate, and it is the
argument of the project: the transport is assumed hostile, and the ledger — not
TLS — is what establishes authenticity.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ...application.ports import FirmwareStorePort
from ...domain import FirmwareFetchFailed, FirmwareImage

#: Refuse absurd payloads outright rather than exhausting memory on a device.
_MAX_IMAGE_BYTES = 32 * 1024 * 1024


class HttpFirmwareStore(FirmwareStorePort):
    """Fetches firmware over plain HTTP or HTTPS."""

    _SCHEMES = ("http://", "https://")

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    def supports(self, locator: str) -> bool:
        return locator.startswith(self._SCHEMES)

    def fetch(self, locator: str) -> FirmwareImage:
        try:
            request = urllib.request.Request(
                locator, headers={"User-Agent": "SecureOTA-Device/1.0"}
            )
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                payload = response.read(_MAX_IMAGE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise FirmwareFetchFailed(f"{locator} returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise FirmwareFetchFailed(f"could not reach {locator}: {exc}") from exc

        if len(payload) > _MAX_IMAGE_BYTES:
            raise FirmwareFetchFailed(f"{locator} exceeds the {_MAX_IMAGE_BYTES}B limit")
        if not payload:
            raise FirmwareFetchFailed(f"{locator} returned an empty body")

        return FirmwareImage(payload=payload, source=locator)


class FileFirmwareStore(FirmwareStorePort):
    """Reads firmware from disk — a USB stick, an SD card, a local mirror."""

    def supports(self, locator: str) -> bool:
        return locator.startswith("file://") or Path(locator).expanduser().is_file()

    def fetch(self, locator: str) -> FirmwareImage:
        raw = locator
        if locator.startswith("file://"):
            raw = urllib.parse.unquote(urllib.parse.urlparse(locator).path)

        path = Path(raw).expanduser()
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise FirmwareFetchFailed(f"could not read {path}: {exc}") from exc

        if not payload:
            raise FirmwareFetchFailed(f"{path} is empty")

        return FirmwareImage(payload=payload, source=str(path))


class IpfsGatewayFirmwareStore(FirmwareStorePort):
    """Resolves ``ipfs://<cid>`` (or a bare CID) through a public gateway.

    The gateway is untrusted infrastructure — a convenience for the demo, not a
    root of trust. Swapping gateways, or being served a malicious response by
    one, changes nothing: the integrity rule still decides.
    """

    def __init__(
        self,
        gateway_url: str = "https://ipfs.io/ipfs/",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._gateway = gateway_url.rstrip("/") + "/"
        self._http = HttpFirmwareStore(timeout_seconds=timeout_seconds)

    def supports(self, locator: str) -> bool:
        return locator.startswith("ipfs://") or self._looks_like_cid(locator)

    def fetch(self, locator: str) -> FirmwareImage:
        cid = locator[len("ipfs://") :] if locator.startswith("ipfs://") else locator
        image = self._http.fetch(self._gateway + cid)
        # Report the logical locator, not the gateway that happened to serve it.
        return FirmwareImage(payload=image.payload, source=f"ipfs://{cid}")

    @staticmethod
    def _looks_like_cid(locator: str) -> bool:
        return (
            locator.startswith(("Qm", "bafy"))
            and "/" not in locator
            and len(locator) >= 46
        )


class RoutingFirmwareStore(FirmwareStorePort):
    """Dispatches to the first adapter that claims the locator.

    Strategy selection at runtime: the use case sees one ``FirmwareStorePort``
    and never learns whether the bytes came from IPFS, a CDN or an SD card.
    """

    def __init__(self, *stores: FirmwareStorePort) -> None:
        if not stores:
            raise ValueError("a routing store needs at least one backing store")
        self._stores = stores

    def supports(self, locator: str) -> bool:
        return any(store.supports(locator) for store in self._stores)

    def fetch(self, locator: str) -> FirmwareImage:
        for store in self._stores:
            if store.supports(locator):
                return store.fetch(locator)
        raise FirmwareFetchFailed(f"no configured store can handle {locator!r}")
