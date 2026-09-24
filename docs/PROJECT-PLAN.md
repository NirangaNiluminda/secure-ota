# SecureOTA — Project Plan

**EC8204 Blockchain and Cyber Security · Group project · 4 members**

Blockchain-anchored firmware update integrity for IoT devices. The manufacturer
publishes a release's SHA-256 fingerprint on-chain; the device verifies what it
downloaded against that fingerprint and refuses to flash anything that does not
match, is older than what it runs, or has been revoked.

---

## 0. Where the build stands

All four packages are implemented and verified together against a contract
deployed on a local node.

| Package | State | Evidence |
|---|---|---|
| `device-client` | complete | 108 tests, no network required |
| `contracts` | complete | 34 tests including ABI conformance |
| `dashboard` | complete | typechecks and builds; layering guard green |
| `attack-harness` | complete | control + 3 attacks pass end to end |

Remaining work is **Stage 4 and 5 only**: deploy to Sepolia, build the deck from
`docs/slides/OUTLINE.md`, rehearse against `docs/demo/RUNBOOK.md`, record the
backup capture, and submit.

---

## 1. The organising idea: freeze the seam, then parallelise

Four people cannot build four packages in six days if each is waiting on the
others. So before anyone writes a feature, the group freezes one artifact:

**`packages/shared/abi/FirmwareRegistry.json`** — the contract's ABI, its
invariants, and the version encoding.

Every package is then written against that ABI, with a fake standing in for
whatever is not built yet. The device client has a `FixtureReleaseRegistry` that
reads a JSON file; the dashboard has a stub registry; the harness has a static
server. Nobody blocks, and integration day is a matter of swapping adapters
rather than discovering that two people assumed different data shapes.

This is why the device client was finished and demonstrable before the contract
was deployed anywhere. It is also the single strongest thing to say about the
engineering when you present.

**The rule:** changing the frozen ABI requires the whole group's agreement and a
`specVersion` bump. It breaks three packages at once.

---

## 2. Architecture

The same layering in every package, dependencies pointing inward only:

```
        cli / ui
            │
      composition root          ← the ONLY place adapters are constructed
            │
   ┌────────┴────────┐
   │   application   │          use cases, ports (interfaces), policies
   │        │        │
   │     domain      │          entities, value objects — stdlib only
   └─────────────────┘
            ▲
     infrastructure              web3, HTTP, IPFS, filesystem, React
```

`domain` imports nothing. `application` imports only `domain`, and depends on
infrastructure exclusively through port interfaces it defines itself
(dependency inversion). `infrastructure` implements those ports. The composition
root wires them together.

This is enforced, not merely documented:
`packages/device-client/tests/unit/test_architecture.py` parses every module's
imports and fails the build the moment a dependency points outward.

### Patterns and where they earn their place

| Pattern | Where | Why it is there, not decoration |
|---|---|---|
| **Ports & Adapters** | `application/ports/` | Lets the device run against a fixture *or* a live chain with zero change above the adapter. This is what unblocked parallel work. |
| **Strategy** | `application/policies/*_rule.py` | One class per threat. Adding a defence adds a file; it does not edit existing code. |
| **Chain of Responsibility** | `VerificationPolicy.evaluate` | Rules run in order and short-circuit at the first refusal. |
| **Composite** | `VerificationPolicy`, `CompositeEventSink`, `RoutingFirmwareStore` | A collection satisfies the same contract as its parts, so it nests invisibly. |
| **Repository** | `DeviceStateRepositoryPort` | Device state is swappable: JSON file today, secure element on real hardware. |
| **Dependency Injection** | constructor injection everywhere | No global state, no singletons, no patching in tests. |
| **Factory / lazy DI** | `DeviceContainer` | `cached_property` builds each adapter at most once, and only if used. |
| **Anti-corruption layer** | `Web3ReleaseRegistry._to_release` | web3 types (`HexBytes`, epoch ints) stop at the boundary and never leak inward. |
| **Result object** | `Verdict`, `UpdateReport` | A refused update is normal control flow, not an exception — so it is testable and demonstrable. |
| **Access Control (RBAC)** | `FirmwareRegistry.sol` | Only `MANUFACTURER_ROLE` may publish or revoke. |

### The design decision worth defending in the viva

The integrity check *fails closed* in every direction. An unreachable ledger,
a missing image, a rule invoked without the bytes it needs — each one refuses
the update and keeps the current firmware. There is no code path in which "we
could not check" becomes "install it anyway". That is the difference between a
security control and a warning message.

---

## 3. Stages

Six working days. Each stage has an exit gate — do not start the next one until
the gate is met.

### Stage 0 — Freeze the seam (Day 0)

*Whole group, together, ~2 hours.*

- Register the topic on the module's Google Sheet.
- Agree the ABI, the version encoding (`major*10000 + minor*100 + patch`), and
  the fixture releases.
- Scaffold the monorepo; everyone clones and runs the device client offline.
- Agree the threat-model table — it is the spine of both the code and the slides.

**Gate:** all four members can run `secure-ota-device --offline status` and see
the same output.

### Stage 1 — Vertical slices against fakes (Days 1–2)

*Everyone in parallel, nobody blocked.*

Each member builds their package end to end using stubs for the others. No
integration attempted yet — resist it, it wastes the two days when parallel work
is cheapest.

**Gate:** each package runs standalone and its tests pass.

### Stage 2 — Real adapters, local integration (Day 3)

- Member 2 deploys to a local Hardhat node and seeds the fixture releases.
- Member 1 swaps `FixtureReleaseRegistry` for `Web3ReleaseRegistry` — a
  one-line change in the composition root, which is the payoff for the layering.
- Member 3 points the dashboard at the local node.
- Member 4 stands up the firmware server.

**Gate:** dashboard publishes → device installs, against a local chain.

### Stage 3 — Testnet and attacks (Day 4)

- Deploy to Sepolia; record the address and verify the contract on Etherscan.
- Member 4's four scenarios all run and assert the right exit codes.
- Fix whatever integration reveals.

**Gate:** all four scenarios pass against Sepolia, scripted and repeatable.

### Stage 4 — Demo, slides, docs (Day 5)

- Build the deck. Rehearse with a timer, out loud, at least three times.
- **Record a screen capture of the full demo as a backup.**
- Write the README and the limitations slide.

**Gate:** a timed run-through lands under 3:00 with the rejection banner clearly
visible.

### Stage 5 — Submit (Day 6)

- File named `GP_XX_SecureOTA.pptx`, uploaded to ELMS.
- One submission for the group. Confirm the real deadline with the coordinator —
  the brief says **31/09/2026**, which is not a date.

---

## 4. Who does what

| | Member | Package | Owns |
|---|---|---|---|
| **1** | *(you)* | `device-client` | The verification agent — domain, rules, use cases, adapters, CLI. The demo's rejection banner. |
| **2** | | `contracts` | `FirmwareRegistry.sol`, Hardhat tests, deploy + seed scripts, Etherscan verification. |
| **3** | | `dashboard` | React manufacturer console: hash in the browser, publish, revoke, release table from events. |
| **4** | | `attack-harness` | Firmware server, four attack scenarios, E2E test, the slide deck and the rehearsal. |

Each package has its own README with a full brief. Member 1's package is
complete and tested; the other three start from their briefs.

### Interfaces between members

| From → To | Artifact |
|---|---|
| 2 → 1, 3 | `deployments/<network>.json` (contract address) |
| 2 → all | The deployed ABI must match the frozen spec |
| 1 → 4 | CLI exit codes: `0` ok, `1` refused, `2` undecided |
| 4 → 1, 3 | Firmware server on `:8081`, locators in the fixture |
| all → 4 | Screenshots and talking points for the deck |

---

## 5. Threat model

The table belongs on a slide, and every row has a test behind it.

| Attack | Conventional OTA | SecureOTA | Enforced by |
|---|---|---|---|
| MITM or compromised CDN swaps the binary | Device installs malware | Hash mismatch → rejected | `IntegrityRule` |
| Downgrade to a vulnerable old release | Signature still valid → accepted | Version monotonicity → rejected | `RollbackRule` + contract |
| Unauthorised party publishes firmware | Server is trusted → accepted | Transaction reverts | `MANUFACTURER_ROLE` |
| Targeted build sent to one victim | Undetectable | Public ledger; everyone sees one hash | Transparency log |
| Vulnerability found after release | Advisory email, unenforced | On-chain revocation, device-enforced | `RevocationRule` |
| Cross-model firmware | Bricks the device | Model mismatch → rejected | `ModelMatchRule` |

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| Campus network or testnet fails mid-demo | `--offline` reproduces every verdict from fixtures; plus a recorded backup |
| Sepolia faucet dry / no test ETH | Get it on Day 3, not Day 5. Local Hardhat is the fallback |
| A member falls behind | The fakes mean their package can be demonstrated stubbed; the seam already isolates it |
| ABI drift between packages | One frozen spec file, `specVersion` bump required to change it, and two automated checks that compare against it |
| 3-minute overrun | Rehearse with a timer from Day 5; cut the problem statement, never the demo |
| `npm install` fails on the repo drive | esbuild ships a native binary and most auto-mounted NTFS/exFAT partitions are `noexec`. Install the dashboard's dependencies on the home partition and symlink them — documented in the dashboard README. Hardhat is pure JS and unaffected |
| No wallet on the presentation machine | Leave `VITE_CONTRACT_ADDRESS` empty; the dashboard's in-memory registry enforces the same rules |

---

## 7. Limitations to state openly

Claiming more than the system does is the fastest way to lose credibility in a
viva. Say these before you are asked:

- **Device state is a plain file.** An attacker who rewrites `installedVersion`
  to `0` defeats rollback protection. Real hardware needs a protected partition,
  an eFuse counter or a secure element.
- **The manufacturer key is a single point of failure.** Stealing it means
  publishing genuine-looking firmware. Multi-sig publishing is the fix, and it
  is listed as future work.
- **The device must trust its RPC endpoint** to report chain state honestly. A
  light client or multiple endpoints would harden this.
- **Availability is not solved.** An attacker who blocks the network stops
  updates. SecureOTA guarantees integrity, not delivery — and it fails closed,
  which is the correct trade.
