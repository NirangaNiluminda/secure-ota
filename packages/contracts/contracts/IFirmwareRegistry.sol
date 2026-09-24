// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IFirmwareRegistry
/// @notice The frozen seam between the contract and every client.
/// @dev This interface is generated from `packages/shared/abi/FirmwareRegistry.json`
///      and must stay byte-compatible with it. Member 2 implements it; the device
///      client, the dashboard and the attack harness are all written against it.
///      Changing a signature here breaks three other packages, so it takes a
///      specVersion bump and agreement from the whole group.
interface IFirmwareRegistry {
    /// @notice One published firmware release.
    /// @param version Monotonic version code. Semantic versions are encoded as
    ///        `major * 10000 + minor * 100 + patch`, so 1.4.0 is 10400. Zero is
    ///        reserved as the "nothing published" sentinel and is never valid.
    /// @param firmwareHash SHA-256 of the exact firmware binary.
    /// @param locator Opaque fetch hint (IPFS CID or HTTPS URL). The chain never
    ///        stores the binary itself — only its fingerprint.
    struct Release {
        uint256 version;
        bytes32 firmwareHash;
        string locator;
        uint256 publishedAt;
        bool revoked;
    }

    /// @dev `model` is an indexed string, so the log topic holds keccak256 of it
    ///      rather than the text. That makes filtering by a known model cheap,
    ///      but the name cannot be recovered from the topic. Clients building a
    ///      release table filter by `keccak256(model)` for models they already
    ///      know; they do not enumerate models from the log.
    event ReleasePublished(
        string indexed model,
        uint256 indexed version,
        bytes32 firmwareHash,
        string locator
    );

    event ReleaseRevoked(string indexed model, uint256 indexed version);

    /// @dev Rollback prevention lives here. Publishing a version that is not
    ///      strictly greater than the current one must revert.
    error NonMonotonicVersion(uint256 provided, uint256 current);
    error UnknownRelease(string model, uint256 version);
    error EmptyFirmwareHash();
    error AlreadyRevoked(string model, uint256 version);

    /// @notice Publish a new release. Restricted to MANUFACTURER_ROLE.
    function publishRelease(
        string calldata model,
        uint256 version,
        bytes32 firmwareHash,
        string calldata locator
    ) external;

    /// @notice Withdraw a release after a vulnerability is disclosed.
    /// @dev One-way. A revoked release can never be un-revoked.
    function revokeRelease(string calldata model, uint256 version) external;

    /// @notice The newest release for a model. Reverts if none exists.
    function latestRelease(string calldata model)
        external
        view
        returns (Release memory);

    /// @notice A specific historical release. Reverts with UnknownRelease if absent.
    function releaseAt(string calldata model, uint256 version)
        external
        view
        returns (Release memory);

    /// @notice The newest version code, or 0 if nothing is published.
    /// @dev Clients call this first so "no release" is a cheap read, not a revert.
    function latestVersion(string calldata model) external view returns (uint256);

    /// @notice How many releases exist for a model.
    function releaseCount(string calldata model) external view returns (uint256);
}
