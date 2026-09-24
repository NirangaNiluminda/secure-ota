# Manufacturer Dashboard — Member 3

The vendor-side console, and the first thirty seconds of the demo: a firmware
file goes in, its SHA-256 appears, a transaction is signed, and the release is
on-chain.

## Running it

```bash
npm install
cp .env.example .env.local     # leave VITE_CONTRACT_ADDRESS empty for demo mode
npm run dev                    # http://localhost:5173
```

With no contract configured it runs against an in-memory registry seeded with the
same three releases the other packages use. That is not a toy: it is how the UI
was built before the contract was deployed, and it is the fallback if the
presentation machine has no wallet installed. It enforces the same monotonicity
and one-way revocation rules as the contract, so demo mode cannot teach the
audience something the real system would not do.

Against a real deployment, set `VITE_CONTRACT_ADDRESS` from
`packages/contracts/deployments/<network>.json`, plus `VITE_RPC_URL` and
`VITE_CHAIN_ID`.

```bash
npm run typecheck        # tsc --noEmit
npm run build            # typecheck + production bundle
npm run check:layering   # architecture guard, see below
```

## ⚠ If the repository lives on a `noexec` mount

`esbuild`, which Vite depends on, ships a native binary that must be executable.
On a drive mounted `noexec` — which includes most auto-mounted NTFS and exFAT
partitions — `npm install` fails with `EACCES ... spawnSync .../esbuild`.

Install the dependencies on a partition that allows execution and link them in:

```bash
mkdir -p ~/.cache/secureota/dashboard-build
cp package.json ~/.cache/secureota/dashboard-build/
(cd ~/.cache/secureota/dashboard-build && npm install)
rm -rf node_modules
ln -sfn ~/.cache/secureota/dashboard-build/node_modules node_modules
```

Do not run `npm install` in the package directory afterwards — it replaces the
symlink. The contracts package is unaffected: Hardhat is pure JavaScript.

## Layout

```
src/
├── domain/              FirmwareVersion, FirmwareHash, Release — plain TS
├── application/
│   ├── ports/           ReleaseRegistryPort, WalletPort, FirmwareHasherPort
│   └── useCases/        PublishRelease, RevokeRelease, ListReleases
├── infrastructure/      EthersReleaseRegistry, BrowserWallet, WebCryptoHasher,
│                        DemoReleaseRegistry — the only place ethers appears
├── composition/         container.ts, the only place adapters are constructed
└── ui/                  components and the App shell
```

Same layering as the device client, for the same reason: `npm run check:layering`
fails the build if any file outside `infrastructure/` imports ethers, and if the
vendored ABI has drifted from `packages/shared`. Architecture that is only
described in a README rots; this one is checked.

## The version encoding

The contract stores a monotonic `uint256`. Every package encodes semantic
versions identically — `major * 10000 + minor * 100 + patch`, so `1.4.0` is
`10400`. It is defined once in `src/domain/FirmwareVersion.ts` and nowhere else.

## Hashing happens here, in the browser

`WebCryptoHasher` computes the digest with `crypto.subtle` the moment a file is
chosen. **The file is never uploaded** — only the 32-byte fingerprint is sent,
and only to the blockchain. Say that out loud during the demo; it is the
difference between SecureOTA and an ordinary upload-and-trust-the-server
pipeline.

## One detail that cost an afternoon elsewhere

`model` is an **indexed string** in the contract's events, so the log topic holds
`keccak256(model)`, not the text. You cannot recover model names from the log.
`EthersReleaseRegistry.listReleases` therefore uses the event log only to
discover *which versions exist*, then reads each one back through `releaseAt` —
which is also the only way to learn whether a release has since been revoked,
since a `ReleasePublished` event cannot know that.

## Demo obligations

- The full digest is shown before the transaction is sent. Pause on it.
- Successful transactions render an Etherscan link. That link is the proof the
  ledger is real, not a local mock.
- The release table marks the version **devices accept** — the newest one not
  withdrawn. Revoking a release visibly moves that marker, which is the payoff
  of the revocation beat.
