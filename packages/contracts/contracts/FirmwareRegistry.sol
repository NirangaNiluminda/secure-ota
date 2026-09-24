// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {IFirmwareRegistry} from "./IFirmwareRegistry.sol";

/// @title FirmwareRegistry
/// @notice The on-chain release register SecureOTA devices verify against.
/// @dev The contract stores only *fingerprints*. Firmware binaries live
///      off-chain — on IPFS, a CDN, an SD card — because putting megabytes
///      on-chain would be absurdly expensive and is not what makes the scheme
///      work. What makes it work is that the fingerprint is public, append-only
///      and identical for every device in the world, so a compromised update
///      server cannot serve one victim a different image than everyone else.
///
///      This is the same principle as Certificate Transparency, applied to
///      embedded firmware.
contract FirmwareRegistry is IFirmwareRegistry, AccessControl {
    /// @notice May publish and revoke releases.
    /// @dev Held by the manufacturer's signing key. Kept separate from
    ///      DEFAULT_ADMIN_ROLE so the key that ships firmware is not also the
    ///      key that manages permissions.
    bytes32 public constant MANUFACTURER_ROLE = keccak256("MANUFACTURER_ROLE");

    /// @dev model => version => release.
    mapping(string => mapping(uint256 => Release)) private _releases;

    /// @dev model => every version ever published, in publication order.
    mapping(string => uint256[]) private _versions;

    /// @dev model => highest version published. Zero means nothing published,
    ///      which is why a valid version is always >= 1.
    mapping(string => uint256) private _latest;

    /// @param admin Receives DEFAULT_ADMIN_ROLE and the initial manufacturer
    ///        role. In production these would be different keys, ideally a
    ///        multisig for the admin.
    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MANUFACTURER_ROLE, admin);
    }

    /// @inheritdoc IFirmwareRegistry
    function publishRelease(
        string calldata model,
        uint256 version,
        bytes32 firmwareHash,
        string calldata locator
    ) external override onlyRole(MANUFACTURER_ROLE) {
        // The single most important line in the project. Because a version must
        // be strictly greater than the current one, an attacker cannot re-publish
        // an old, genuine, correctly-signed but known-vulnerable image. A plain
        // signature check cannot see that attack; an ordering invariant can.
        uint256 current = _latest[model];
        if (version <= current) {
            revert NonMonotonicVersion(version, current);
        }

        if (firmwareHash == bytes32(0)) {
            revert EmptyFirmwareHash();
        }

        // Guarded with a require string rather than a custom error so the error
        // set stays byte-identical to the frozen ABI in packages/shared.
        require(bytes(locator).length != 0, "FirmwareRegistry: empty locator");

        _releases[model][version] = Release({
            version: version,
            firmwareHash: firmwareHash,
            locator: locator,
            publishedAt: block.timestamp,
            revoked: false
        });

        _versions[model].push(version);
        _latest[model] = version;

        emit ReleasePublished(model, version, firmwareHash, locator);
    }

    /// @inheritdoc IFirmwareRegistry
    function revokeRelease(string calldata model, uint256 version)
        external
        override
        onlyRole(MANUFACTURER_ROLE)
    {
        Release storage release = _releases[model][version];
        if (release.version == 0) {
            revert UnknownRelease(model, version);
        }
        if (release.revoked) {
            revert AlreadyRevoked(model, version);
        }

        // One-way by design. A release withdrawn for a vulnerability must not be
        // quietly reinstated; shipping a fix means publishing a new version,
        // which leaves the withdrawal permanently on the public record.
        release.revoked = true;

        emit ReleaseRevoked(model, version);
    }

    /// @inheritdoc IFirmwareRegistry
    function latestRelease(string calldata model)
        external
        view
        override
        returns (Release memory)
    {
        uint256 version = _latest[model];
        if (version == 0) {
            revert UnknownRelease(model, 0);
        }
        return _releases[model][version];
    }

    /// @inheritdoc IFirmwareRegistry
    function releaseAt(string calldata model, uint256 version)
        external
        view
        override
        returns (Release memory)
    {
        Release memory release = _releases[model][version];
        if (release.version == 0) {
            revert UnknownRelease(model, version);
        }
        return release;
    }

    /// @inheritdoc IFirmwareRegistry
    /// @dev Returns 0 rather than reverting so a device can ask "is there
    ///      anything for me?" with one cheap call and no revert handling.
    function latestVersion(string calldata model)
        external
        view
        override
        returns (uint256)
    {
        return _latest[model];
    }

    /// @inheritdoc IFirmwareRegistry
    function releaseCount(string calldata model)
        external
        view
        override
        returns (uint256)
    {
        return _versions[model].length;
    }

    /// @notice The version published at `index`, in publication order.
    /// @dev Not part of the frozen client ABI. Convenience for enumerating a
    ///      model's history without replaying the event log.
    function versionAt(string calldata model, uint256 index)
        external
        view
        returns (uint256)
    {
        return _versions[model][index];
    }
}
