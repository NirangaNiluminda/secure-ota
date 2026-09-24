# Manufacturer Dashboard — Member 3

The vendor-side console. This is what the audience watches during the first
thirty seconds of the demo: a firmware file goes in, a hash appears, a
transaction is signed, and the release is on-chain.

## Your deliverable

A single-page app with three screens:

1. **Publish** — drag in a `.bin`, the page computes SHA-256 *in the browser*,
   shows it, and calls `publishRelease`. Never upload the file to compute the
   hash; computing it client-side is the point.
2. **Releases** — a table of every release for a model, read from
   `ReleasePublished` / `ReleaseRevoked` events, with the revoked ones struck
   through.
3. **Revoke** — pick a version, confirm, call `revokeRelease`.

## Setup

```bash
npm create vite@latest . -- --template react-ts
npm i ethers
```

## Structure — mirror the device client's layering

```
src/
├── domain/              Release, FirmwareVersion, FirmwareHash (plain TS, no ethers)
├── application/ports/   ReleaseRegistryPort, WalletPort  (interfaces)
├── infrastructure/      EthersReleaseRegistry, MetaMaskWallet  (implements the ports)
└── ui/                  components and pages — no ethers imports anywhere here
```

The rule that matters: **no React component may import `ethers` directly.** A
component calls a port; the port is implemented in `infrastructure/`. That keeps
the UI testable and means swapping MetaMask for WalletConnect touches one file.
It also means your layering argument matches Member 1's, which reads as one
system rather than two projects stapled together.

## Hashing in the browser

```ts
const buffer = await file.arrayBuffer();
const digest = await crypto.subtle.digest("SHA-256", buffer);
const hex = "0x" + [...new Uint8Array(digest)]
  .map(b => b.toString(16).padStart(2, "0")).join("");
```

Show that hex string prominently before the transaction is sent — the audience
needs to see the same value land on Etherscan.

## Version encoding

The contract stores a monotonic `uint256`. Encode semantic versions exactly as
the other packages do, or the integration breaks:

```ts
const toCode = (major: number, minor: number, patch: number) =>
  major * 10000 + minor * 100 + patch;   // 1.4.0 -> 10400
```

## Config

Read the contract address from `deployments/<network>.json` that Member 2
produces. Do not hard-code it, and do not commit any private key or RPC key —
`.env` is gitignored for a reason.

## Demo obligations

- The publish button must show a pending state and then a link to the
  transaction on Etherscan. That link is the proof the ledger is real.
- Keep the UI legible from the back of a room: large type, high contrast, no
  dense tables.
