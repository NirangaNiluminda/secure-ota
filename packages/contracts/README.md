# FirmwareRegistry Contract — Member 2

You own the root of trust. Everything the other three packages do is verification
*against* what this contract stores.

## Your deliverable

Implement [`contracts/IFirmwareRegistry.sol`](contracts/IFirmwareRegistry.sol).
That interface is already frozen and generated from
`packages/shared/abi/FirmwareRegistry.json` — do not change either without telling
the group, because three other packages are compiled against it.

```
contracts/FirmwareRegistry.sol   your implementation
test/FirmwareRegistry.t.ts       Hardhat tests
scripts/deploy.ts                deploy + write the address to deployments/
scripts/seed.ts                  publish the three fixture releases
```

## Setup

```bash
npm init -y
npm i -D hardhat @nomicfoundation/hardhat-toolbox
npm i @openzeppelin/contracts
npx hardhat init      # TypeScript, keep it minimal
```

## Design notes

Use OpenZeppelin `AccessControl` with a `MANUFACTURER_ROLE`. The deployer gets
`DEFAULT_ADMIN_ROLE` and grants the manufacturer role; that separation is worth a
sentence in the presentation.

Storage shape:

```solidity
mapping(string => mapping(uint256 => Release)) private _releases;
mapping(string => uint256[]) private _versions;   // publication order
mapping(string => uint256)  private _latest;      // 0 = nothing published
```

The single most important line in the whole project:

```solidity
if (version <= _latest[model]) revert NonMonotonicVersion(version, _latest[model]);
```

That is what makes a downgrade unrepresentable at the protocol level rather than
merely discouraged. Say exactly that when you present it.

Other requirements:

- Reject `bytes32(0)` as a firmware hash (`EmptyFirmwareHash`).
- `revokeRelease` is one-way; re-revoking reverts with `AlreadyRevoked`.
- `latestVersion` returns `0` rather than reverting, so clients get a cheap
  "nothing published" answer without catching a revert.
- Emit `ReleasePublished` / `ReleaseRevoked` on every mutation. The event log *is*
  the public audit trail, and the dashboard reads it.
- Use custom errors, not `require` strings — cheaper, and it shows you know the
  difference.

## Tests to write

Mirror the device client's scenario matrix so both sides prove the same
properties:

1. A non-manufacturer calling `publishRelease` reverts.
2. Publishing an equal or lower version reverts with `NonMonotonicVersion`.
3. Publishing a strictly higher version succeeds and updates `latestVersion`.
4. `latestVersion` is `0` for an unknown model.
5. `releaseAt` on an unknown version reverts with `UnknownRelease`.
6. Revoking flips the flag and emits; revoking twice reverts.
7. A zero firmware hash reverts.

## Hand-off to the others

When you deploy, write the address and network into
`deployments/<network>.json`. Member 1 reads it via `--contract`, Member 3 via
the dashboard config. Seed with the digests printed by
`python3 scripts/build_fixtures.py` at the repo root so all four packages agree
on the same three releases.
