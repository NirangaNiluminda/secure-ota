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

## Layout

| Package | Owner | What it is |
|---|---|---|
| [`packages/device-client`](packages/device-client/) | Member 1 | The verification agent. Complete, 108 tests passing. |
| [`packages/contracts`](packages/contracts/) | Member 2 | `FirmwareRegistry.sol` — the on-chain release register. |
| [`packages/dashboard`](packages/dashboard/) | Member 3 | Manufacturer console: publish and revoke releases. |
| [`packages/attack-harness`](packages/attack-harness/) | Member 4 | Firmware server, attack scenarios, E2E test, slides. |
| [`packages/shared`](packages/shared/) | all | The frozen ABI and the golden fixtures every package agrees on. |

Each package README is a full brief for its owner.

## Start here

- [`docs/PROJECT-PLAN.md`](docs/PROJECT-PLAN.md) — stages, member split, threat
  model, risks, and the limitations to state openly.
- [`packages/shared/abi/FirmwareRegistry.json`](packages/shared/abi/FirmwareRegistry.json)
  — the frozen seam. Changing it breaks three packages, so it takes a group
  decision and a `specVersion` bump.

## Regenerating the fixtures

```bash
python3 scripts/build_fixtures.py
```

Writes the firmware binaries and prints the digests to seed the contract with.
Bytes and hashes come from one source, so a fixture can never describe a file it
does not match.
