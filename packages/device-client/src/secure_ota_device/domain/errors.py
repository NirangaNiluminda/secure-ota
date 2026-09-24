"""Domain-level exceptions.

Reserved for conditions that genuinely prevent the device from reaching a
verdict at all — an unreachable ledger, an unreadable state file. A refused
update is *not* an error; it is a :class:`~.verdicts.Verdict`.
"""

from __future__ import annotations


class SecureOtaError(Exception):
    """Base class for every SecureOTA failure."""


class RegistryUnavailable(SecureOtaError):
    """The release registry could not be queried.

    Fail closed: when the device cannot reach the ledger it keeps running the
    firmware it already trusts rather than accepting an unverified image.
    """


class FirmwareFetchFailed(SecureOtaError):
    """The firmware image could not be retrieved from its locator."""


class DeviceStateCorrupt(SecureOtaError):
    """The persisted device state could not be read or parsed."""


class InstallationFailed(SecureOtaError):
    """The verified image could not be written to the firmware slot."""
