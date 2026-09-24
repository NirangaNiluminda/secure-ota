# SecureOTA Device Agent — Member 1

The embedded-side agent. It asks the blockchain what a firmware release *should*
be, fetches the image from an untrusted source, and refuses to install it unless
the bytes match. This is the package that produces the demo's rejection banner.

## Running it

No dependencies are required for the offline path — a bare Python 3.10+ install
is enough.

```bash
export PYTHONPATH=src

# What is this device running, and what does it defend against?
python3 -m secure_ota_device.cli.main --offline status

# Verify the latest release without installing (dry run)
python3 -m secure_ota_device.cli.main --offline check

# Verify and install
python3 -m secure_ota_device.cli.main --offline update
```

Against a real chain, drop `--offline` and supply the deployment:

```bash
python3 -m secure_ota_device.cli.main \
  --rpc-url https://sepolia.infura.io/v3/$KEY \
  --contract 0xYourFirmwareRegistry \
  update
```

`--offline` is not a toy mode. It is a first-class adapter that reads
`packages/shared/fixtures/sample-releases.json`, and it is the rehearsed
fallback if the network fails during the live presentation — the verdicts are
identical either way.

Exit codes: `0` success, `1` update refused, `2` could not decide.

## Layout

```
src/secure_ota_device/
├── domain/          entities, value objects, verdicts — stdlib only
├── application/
│   ├── ports/       the five abstractions everything plugs into
│   ├── policies/    one class per security rule
│   └── use_cases/   the update cycle orchestrator
├── infrastructure/  web3, HTTP, IPFS, filesystem adapters
├── composition/     the only place adapters are constructed
└── cli/             argument parsing and rendering, no logic
```

Dependencies point inward only, and
[`tests/unit/test_architecture.py`](tests/unit/test_architecture.py) fails the
build if that ever stops being true.

## The rules

Each maps to one row of the threat model, and each is a separate class:

| Rule | Stage | Defends against |
|---|---|---|
| `model-match` | pre-fetch | Cross-model firmware swap that bricks the device |
| `revocation` | pre-fetch | Installing a release withdrawn after a CVE |
| `rollback` | pre-fetch | Downgrade to a genuine but known-vulnerable release |
| `integrity` | post-fetch | Tampered binary from a compromised server or network |

The pre-fetch/post-fetch split means a bad update is refused after two cheap
ledger reads, before any bandwidth is spent. Only the hash check needs the bytes.

## Tests

```bash
python3 -m pytest        # 108 tests, no network, no chain
```

The suite includes a scenario for every attack in the presentation, so a
regression in any defence fails the build rather than the demo.

## Known limitation

`JsonFileDeviceStateRepository` keeps the installed version in a plain file. An
attacker who can rewrite it to `0` defeats rollback protection. On real hardware
this belongs in a protected partition, an eFuse counter or a secure element.
This is stated on the limitations slide rather than glossed over.
