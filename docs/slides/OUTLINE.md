# GP_XX_SecureOTA.pptx — Slide Outline

Eight slides for three minutes. That is roughly twenty seconds each, and two of
them are live demo, so the rest must be almost wordless. **Nothing on a slide
you are going to say out loud.**

---

### 1 — Title

> **SecureOTA**
> Blockchain-Anchored Firmware Update Integrity for IoT Devices
>
> EC8204 · Group XX · four names and registration numbers

---

### 2 — The problem *(≈20s)*

One image: device → arrow → vendor server, with the arrow labelled **"trusted
blindly"**.

Three lines, no more:

- IoT devices install whatever their update server sends
- Compromise the server and you own the fleet — ASUS, ~1 million machines
- Code signing does not help: it proves *who built* it, not *whether it is current*

---

### 3 — Threat model *(≈20s)*

The table. This is the spine of the whole project — every row has code and a test
behind it.

| Attack | Conventional OTA | SecureOTA |
|---|---|---|
| CDN swaps the binary | installs malware | hash mismatch → rejected |
| Downgrade to vulnerable release | signature valid → accepted | version ordering → rejected |
| Unauthorised publisher | server is trusted | transaction reverts |
| Targeted build for one victim | undetectable | public ledger, one hash for all |
| Vulnerability found post-release | advisory email | on-chain revocation, enforced |

---

### 4 — How it works *(≈20s)*

One diagram, four boxes:

```
Manufacturer ──SHA-256──▶ Blockchain (fingerprint only)
     │                          │
     ▼                          ▼
  IPFS / CDN ──bytes──▶  Device: re-hash, compare, refuse or flash
```

The single sentence that carries it:

> **The binary lives off-chain. Only its fingerprint goes on-chain — and that is
> enough.**

---

### 5 — LIVE DEMO *(1:40 of the 3:00)*

One word on the slide: **DEMO**. Everything else is the runbook.

Publish → honest update → tampered binary → rollback → revocation.

---

### 6 — Engineering *(≈15s)*

Four packages, clean architecture in each, dependencies pointing inward only.

- **142 automated tests** — 108 Python, 34 Solidity
- The layering is **enforced by a test**, not described in a README
- One frozen ABI is the seam: four people built in parallel against fakes
- Verified end to end — Python device client against the real deployed contract

---

### 7 — Limitations *(≈15s)*

State these before you are asked. Claiming more than the system does is the
fastest way to lose a viva.

- Device state is a writable file — real hardware needs a secure element
- A single manufacturer key is a single point of failure — multisig is the fix
- The device trusts its RPC endpoint to report chain state honestly
- Integrity is guaranteed; **availability is not** — and it fails closed

---

### 8 — Future work / close

- Multisig release approval; staged rollout gated on install receipts
- Device attestation — signed install receipts giving a verifiable fleet inventory
- Real ESP32 target

Closing line:

> When SecureOTA cannot verify an update, it refuses it. There is no path where
> "could not check" becomes "install anyway" — and that is the difference between
> a security control and a warning message.

---

## Rules for building the deck

- **No paragraphs.** If a slide has a sentence you will read aloud, cut it.
- Dark background, large type — it will be projected, possibly badly.
- Screenshots of the red `HASH_MISMATCH` banner on slides 3 and 7 as insurance,
  so the story survives even if the live demo cannot run.
- Save as `GP_XX_SecureOTA.pptx` with your actual group number.
- One submission per group to ELMS. Last upload before the deadline counts.
