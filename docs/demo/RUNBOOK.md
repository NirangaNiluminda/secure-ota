# SecureOTA — Demo Runbook

Three minutes. Rehearse it with a timer, out loud, at least three times. The most
common way this goes wrong is spending ninety seconds on the problem statement
and rushing the part that actually demonstrates something.

---

## Setup, 20 minutes before

Four terminals and a browser. Set them up before the session starts, not during.

**Terminal 1 — the chain**

```bash
cd packages/contracts
npm run node
```

**Terminal 2 — deploy and seed** (then keep it for ad-hoc commands)

```bash
cd packages/contracts
npm run deploy:local && npm run seed:local
```

**Terminal 3 — the untrusted firmware server.** Keep this visible: it prints the
SHA-256 of every file it serves, so the audience watches the digest change the
instant you tamper.

```bash
cd packages/attack-harness
bash scenarios/00-start-server.sh
```

**Terminal 4 — the device.** Large font. This is where the red banner appears.

**Browser** — the dashboard at `http://localhost:5173`, wallet connected.

```bash
cd packages/dashboard && npm run dev
```

### Preflight — run this and confirm it is green

```bash
cd packages/attack-harness
PYTHON=/path/to/python-with-web3 bash run-e2e.sh
```

If that prints `ALL SCENARIOS PASSED`, the demo works. If it does not, fix it
before you present — do not improvise on stage.

---

## The three minutes

### 0:00–0:40 — the problem

Slides only. Do not touch a terminal yet.

> Every connected device pulls firmware over the air and trusts whatever the
> vendor's server hands it. Compromise that server — as happened to ASUS, where
> roughly a million machines took a malicious update through the legitimate
> channel — and every device installs your code.
>
> Code signing does not fix it. A signature proves *who built* an image, not
> whether it is the *current* release, and not whether everyone received the
> same one.

Show the threat-model table. Move on.

### 0:40–1:10 — publish

Browser. Drag in `RUH-SENSOR-01-1.5.0.bin`.

> The hash is computed here, in the browser. The file is never uploaded — only
> this 32-byte fingerprint goes on-chain.

Point at the digest. Click **Publish**. Show the transaction.

### 1:10–1:40 — an honest update

Terminal 4:

```bash
bash scenarios/01-happy-path.sh
```

> The device asks the ledger what v1.4.0 should hash to, downloads the image
> from a server it does not trust, hashes it locally, and the values match.

Green `INSTALLED`.

### 1:40–2:20 — the attacks ⚡ the part that matters

```bash
bash scenarios/02-tampered-binary.sh
```

> I am now the attacker. I have compromised the CDN and replaced the image.
> Same filename, same version, same URL. Only the bytes changed.

Red `HASH_MISMATCH`. **Pause here.** Let it land.

```bash
bash scenarios/03-rollback.sh
```

> Now I serve a *genuine* image — correctly signed, authentically the vendor's —
> but it is v1.2.0, whose vulnerability is public. A signature check passes this.
> Version ordering does not.

Red `ROLLBACK_BLOCKED`.

### 2:20–3:00 — revocation, limits, close

Browser: revoke v1.4.0. Then terminal:

```bash
bash scenarios/04-revoked-release.sh
```

> A vulnerability is found after release. Today that is an advisory email most
> fleets never act on. Here it is a ledger state change every device reads and
> enforces by itself.

Close on the limitations slide — writable device state, single manufacturer key,
trust in the RPC endpoint, no availability guarantee — then one line:

> SecureOTA guarantees integrity, not delivery. And when it cannot verify, it
> refuses. That is the correct trade.

---

## If something breaks

| Problem | Do this |
|---|---|
| Network or testnet down | `--offline` on the device client reproduces every verdict from local fixtures. Same output, no chain. |
| Wallet missing or broken | Leave `VITE_CONTRACT_ADDRESS` empty; the dashboard runs on the in-memory registry with the same rules. |
| Anything else | Play the recorded screen capture. **Record it the day before.** |

Do not debug on stage. Switch to the fallback, narrate it, keep moving.

---

## Rehearsal checklist

- [ ] `run-e2e.sh` green on the presentation machine
- [ ] Terminal font large enough to read from the back row
- [ ] Screen capture of the full demo recorded and playable offline
- [ ] Timed run-through under 3:00, three times
- [ ] Everyone knows who speaks when
