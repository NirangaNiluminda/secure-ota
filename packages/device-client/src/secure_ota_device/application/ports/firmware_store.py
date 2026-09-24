"""Port: where firmware bytes are fetched from.

This is the deliberately *untrusted* boundary of the system. IPFS gateway, vendor
CDN, plain HTTP, a USB stick — SecureOTA's whole argument is that it does not
matter, because the bytes are checked against the ledger regardless.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain import FirmwareImage


class FirmwareStorePort(ABC):
    """Retrieves firmware images from an untrusted location."""

    @abstractmethod
    def fetch(self, locator: str) -> FirmwareImage:
        """Download the image identified by ``locator``.

        Raises:
            FirmwareFetchFailed: if the image cannot be retrieved. The caller
                keeps the current firmware; it never installs a partial image.
        """

    @abstractmethod
    def supports(self, locator: str) -> bool:
        """Whether this adapter can handle the given locator scheme."""
