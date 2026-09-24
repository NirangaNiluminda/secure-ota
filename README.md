# SecureOTA

**Blockchain-anchored firmware update integrity for IoT devices**

EC8204 Blockchain and Cyber Security · University of Ruhuna, Department of
Electrical & Information Engineering

---

Connected devices pull firmware over the air and trust whatever their vendor's
server hands them. If that server, its CDN or the network path is compromised,
the device installs attacker-controlled firmware and is owned permanently. Code
signing does not fix this: a signature proves *who built* an image, not whether
it is the *current* release, and not whether everybody received the same one.

SecureOTA publishes each release's SHA-256 fingerprint to a public ledger and
never the binary itself. The device downloads from anywhere, recomputes the hash
locally, and refuses to flash anything that does not match — or that is older
than what it runs, or that the vendor has revoked.

The same principle as Certificate Transparency and binary transparency, applied
to embedded firmware.

## Demo in thirty seconds

No dependencies required:

```bash
cd packages/device-client
export PYTHONPATH=src

python3 -m secure_ota_device.cli.main --offline status
python3 -m secure_ota_device.cli.main --offline update     # ✓ INSTALLED
```

Then tamper with the image and watch it refuse:

```bash
echo "MALICIOUS" > ../shared/fixtures/firmware/RUH-SENSOR-01-1.4.0.bin
python3 -m secure_ota_device.cli.main --offline update     # ⚠ HASH_MISMATCH
git checkout ../shared/fixtures/firmware                   # restore
```

## The full stack

Four terminals. Detailed steps in [`docs/demo/RUNBOOK.md`](docs/demo/RUNBOOK.md).

```bash
# 1. chain
cd packages/contracts && npm install && npm run node

# 2. deploy + seed the three fixture releases
cd packages/contracts && npm run deploy:local && npm run seed:local

# 3. the untrusted firmware server
cd packages/attack-harness && bash scenarios/00-start-server.sh

# 4. every defence, end to end
cd packages/attack-harness && PYTHON=$(which python3) bash run-e2e.sh
```

The dashboard runs separately with `cd packages/dashboard && npm run dev`.

## Layout

| Package | Owner | What it is | Status |
|---|---|---|---|
| [`packages/device-client`](packages/device-client/) | Member 1 | The verification agent — Python, clean architecture | 108 tests ✅ |
| [`packages/contracts`](packages/contracts/) | Member 2 | `FirmwareRegistry.sol` — the on-chain release register | 34 tests ✅ |
| [`packages/dashboard`](packages/dashboard/) | Member 3 | Manufacturer console: hash in-browser, publish, revoke | builds clean ✅ |
| [`packages/attack-harness`](packages/attack-harness/) | Member 4 | Firmware server, 4 scenarios, E2E runner | all passing ✅ |
| [`packages/shared`](packages/shared/) | all | The frozen ABI and the golden fixtures every package agrees on | — |

Each package README documents its own design and the traps it hit.

## Verifying everything

```bash
cd packages/device-client && python3 -m pytest          # 108 tests, no network
cd packages/contracts     && npm test                   # 34 tests, incl. ABI conformance
cd packages/dashboard     && npm run build              # typecheck + bundle
cd packages/dashboard     && npm run check:layering     # architecture guard
cd packages/attack-harness && bash run-e2e.sh           # all four packages together
```

## Start here

- [`docs/PROJECT-PLAN.md`](docs/PROJECT-PLAN.md) — stages, member split, threat
  model, risks, and the limitations to state openly.
- [`docs/demo/RUNBOOK.md`](docs/demo/RUNBOOK.md) — the three-minute demo, minute
  by minute, with the fallbacks if the network dies.
- [`docs/slides/OUTLINE.md`](docs/slides/OUTLINE.md) — eight slides.
- [`packages/shared/abi/FirmwareRegistry.json`](packages/shared/abi/FirmwareRegistry.json)
  — the frozen seam. Changing it breaks three packages, so it takes a group
  decision and a `specVersion` bump.

## Architecture in one rule

Every package layers the same way, dependencies pointing inward only:

```
   cli / ui  →  composition  →  application  →  domain
                        ↘   infrastructure   ↗
```

`domain` imports nothing. `application` defines the ports it needs and never
learns what implements them. This is enforced, not documented:
[`test_architecture.py`](packages/device-client/tests/unit/test_architecture.py)
parses every Python import and
[`check-layering.mjs`](packages/dashboard/scripts/check-layering.mjs) does the
same for TypeScript. Both fail the build on a violation.

## Regenerating the fixtures

```bash
python3 scripts/build_fixtures.py
```

Writes the firmware binaries and prints the digests to seed the contract with.
Bytes and hashes come from one source, so a fixture can never describe a file it
does not match.
