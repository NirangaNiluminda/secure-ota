# Attack Harness & Demo Orchestration — Member 4

You play the attacker, and you own the three minutes in front of the examiners.
This is not a support role: the defences the other three built prove nothing
until something credible attacks them.

## Your deliverables

### 1. A firmware server (the untrusted source)

A dead-simple HTTP server on `:8081` that serves files from a directory. That
directory is what you tamper with. It stands in for the vendor CDN or the IPFS
gateway — infrastructure the project deliberately does not trust.

### 2. Four attack scenarios, each one command

```
scenarios/01-tampered-binary.sh    swap the served .bin for a malicious one
scenarios/02-rollback.sh           steer the device at an older genuine release
scenarios/03-revoked-release.sh    offer a release the vendor withdrew
scenarios/04-happy-path.sh         the control: an honest update succeeds
```

Each script prints what the attacker is doing, runs the device client, and shows
the verdict. The control case matters as much as the attacks — without it, the
audience cannot tell a working defence from a device that refuses everything.

### 3. End-to-end integration test

One script that runs the full stack — local Hardhat node, deployed contract,
seeded releases, firmware server, device client — and asserts the exit codes:
`0` for the happy path, `1` for each attack. Wire it so a failure is loud.

### 4. The presentation

`GP_XX_SecureOTA.pptx`, three minutes, and the rehearsal that makes it fit.

## Running the device client from a scenario

```bash
export PYTHONPATH=../device-client/src
python3 -m secure_ota_device.cli.main \
  --state .serve/state.json --slot .serve/slot \
  --contract "$CONTRACT" --rpc-url http://127.0.0.1:8545 \
  update
echo "exit=$?"      # 1 means the device refused — that is a pass
```

To reset the device between scenarios, write the state file directly:

```bash
printf '{"model":"RUH-SENSOR-01","installedVersion":10200}' > .serve/state.json
```

## Suggested three-minute running order

| Time | Beat |
|---|---|
| 0:00–0:40 | Problem + threat-model table |
| 0:40–1:10 | Member 3 publishes v1.4.0; show the tx on Etherscan |
| 1:10–1:40 | Device updates cleanly — green `INSTALLED` |
| 1:40–2:20 | **You swap the binary. Red `HASH_MISMATCH`.** Then the downgrade. |
| 2:20–3:00 | Revocation, limitations, future work |

Rehearse with a timer. Three minutes is much shorter than it sounds, and the
single most common way this goes wrong is spending ninety seconds on the problem
statement and rushing the part that actually demonstrates something.

## Non-negotiable

Have a recorded screen capture of the full demo as a backup, and know that
`--offline` reproduces every verdict from local fixtures if the network dies.
Do not let a dropped Wi-Fi connection cost the group its marks.
