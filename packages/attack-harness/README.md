# Attack Harness & Demo Orchestration — Member 4

You play the attacker, and you own the three minutes in front of the examiners.
This is not a support role: the defences the other three built prove nothing
until something credible attacks them.

## Your deliverables

### 1. A firmware server (the untrusted source)

A dead-simple HTTP server on `:8081` that serves files from a directory. That
directory is what you tamper with. It stands in for the vendor CDN or the IPFS
gateway — infrastructure the project deliberately does not trust.

### 2. Four scenarios, each one command

```
scenarios/00-start-server.sh       the untrusted firmware server (foreground)
scenarios/01-happy-path.sh         the control: an honest update succeeds
scenarios/02-tampered-binary.sh    swap the served .bin for an implant
scenarios/03-rollback.sh           steer the device at an older genuine release
scenarios/04-revoked-release.sh    offer a release the vendor withdrew
```

Each script prints what the attacker is doing, runs the device client, and
**asserts its own expected outcome**, exiting non-zero if the defence did not
behave. That way the same script serves the live demo and CI — a defence that
quietly stopped working is caught here rather than on stage.

The control case matters as much as the attacks. Without it, the audience cannot
tell a working defence from a device that refuses everything.

### 3. End-to-end integration test

`run-e2e.sh` starts the firmware server, runs the control and all three attacks
against the deployed contract, and fails loudly if any defence misbehaves. This
is the Stage 3 gate: if it is green, the demo works.

### 4. The presentation

`GP_XX_SecureOTA.pptx`, three minutes, and the rehearsal that makes it fit.

## Running it

The device client needs `web3` to talk to a chain, so point `PYTHON` at an
interpreter that has it. Note that if the repository lives on a drive mounted
`noexec`, invoke the scripts through `bash` rather than executing them directly.

First, from `packages/contracts`:

```bash
npm run node                                 # in its own terminal
npm run deploy:local && npm run seed:local
```

Then, from here:

```bash
PYTHON=/path/to/python-with-web3 bash run-e2e.sh      # everything at once

bash scenarios/00-start-server.sh                     # or, for the live demo:
PYTHON=... bash scenarios/02-tampered-binary.sh       # one beat at a time
```

`_common.sh` resolves the contract address from
`packages/contracts/deployments/localhost.json`, so nothing is hard-coded.
Override with `CONTRACT=0x...` to point at Sepolia.

Exit codes: `0` means the scenario behaved as expected — including the attacks,
where the expected behaviour is that the device *refused*.

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
