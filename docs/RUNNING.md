# Running SecureOTA

Three levels, depending on how much you need. Start at level 1 — it needs
nothing installed and still shows every defence working.

---

## Level 1 — offline, zero setup *(30 seconds)*

No npm, no blockchain, no dependencies. Just Python 3.10+.

```bash
cd packages/device-client
export PYTHONPATH=src

python3 -m secure_ota_device.cli.main --offline status
python3 -m secure_ota_device.cli.main --offline update       # ✓ INSTALLED
```

Now play attacker:

```bash
echo "MALICIOUS" > ../shared/fixtures/firmware/RUH-SENSOR-01-1.4.0.bin
python3 -m secure_ota_device.cli.main --offline update       # ⚠ HASH_MISMATCH
git checkout ../shared/fixtures/firmware                     # restore
```

`--offline` reads releases from `packages/shared/fixtures/` instead of a chain.
The verdicts are identical to the live path, which is why it is the rehearsed
fallback if the network dies during the presentation.

---

## Level 2 — the test suites

### Python (device client)

The repository may live on a drive mounted `noexec`, where a venv's scripts
cannot execute. Put the venv on your home partition:

```bash
python3 -m venv ~/.cache/secureota/venv
~/.cache/secureota/venv/bin/pip install pytest 'web3>=6.15,<8'

cd packages/device-client
~/.cache/secureota/venv/bin/python -m pytest      # 108 passed
```

`web3` is only needed to talk to a real chain. The tests and the offline demo
run on a bare Python install, which is deliberate — it keeps the unit tests
honest, because they physically cannot reach a network.

### Solidity (contracts)

```bash
cd packages/contracts
npm install
npm test          # 34 passed, including ABI conformance
```

### TypeScript (dashboard)

```bash
cd packages/dashboard
npm install
npm run build            # typecheck + production bundle
npm run check:layering   # architecture guard
```

> **If `npm install` fails with `EACCES ... spawnSync .../esbuild`** your drive is
> mounted `noexec` and esbuild's native binary cannot run. Install elsewhere and
> link it in:
>
> ```bash
> mkdir -p ~/.cache/secureota/dashboard-build
> cp package.json ~/.cache/secureota/dashboard-build/
> (cd ~/.cache/secureota/dashboard-build && npm install)
> rm -rf node_modules
> ln -sfn ~/.cache/secureota/dashboard-build/node_modules node_modules
> ```
>
> Do not run `npm install` in the package directory afterwards — it replaces the
> symlink. Hardhat is unaffected; it is pure JavaScript.

---

## Level 3 — the full stack

Four terminals. This is what the demo runs on.

**Terminal 1 — local blockchain**

```bash
cd packages/contracts
npm run node                      # Hardhat node on :8545
```

**Terminal 2 — deploy and seed**

```bash
cd packages/contracts
npm run deploy:local              # writes deployments/localhost.json
npm run seed:local                # publishes v1.2.0, v1.3.0, v1.4.0; revokes v1.3.0
```

**Terminal 3 — the untrusted firmware server**

```bash
cd packages/attack-harness
bash scenarios/00-start-server.sh   # :8081, logs the SHA-256 of everything it serves
```

**Terminal 4 — the device, and the attacks**

```bash
cd packages/attack-harness
export PYTHON=~/.cache/secureota/venv/bin/python

bash run-e2e.sh                     # everything: control + 3 attacks

# or one beat at a time, for the live demo:
bash scenarios/01-happy-path.sh      # ✓ INSTALLED          exit 0
bash scenarios/02-tampered-binary.sh # ⚠ HASH_MISMATCH      exit 1
bash scenarios/03-rollback.sh        # ⚠ ROLLBACK_BLOCKED   exit 1
bash scenarios/04-revoked-release.sh # ⚠ RELEASE_REVOKED    exit 1
```

**Browser — the manufacturer console**

```bash
cd packages/dashboard
cp .env.example .env.local
# set VITE_CONTRACT_ADDRESS from packages/contracts/deployments/localhost.json
npm run dev                       # http://localhost:5173
```

Leaving `VITE_CONTRACT_ADDRESS` empty runs the dashboard against an in-memory
registry with the same rules — the fallback if the machine has no wallet.

### Driving the device by hand

```bash
cd packages/device-client
export PYTHONPATH=src
ADDR=$(python3 -c "import json;print(json.load(open('../contracts/deployments/localhost.json'))['address'])")

~/.cache/secureota/venv/bin/python -m secure_ota_device.cli.main \
  --contract "$ADDR" --rpc-url http://127.0.0.1:8545 status
```

Exit codes: `0` success, `1` update refused, `2` could not decide.

---

## Deploying to a testnet

```bash
cd packages/contracts
cp .env.example .env              # SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY
npm run deploy:sepolia
npm run seed:sepolia
```

Use a throwaway key that holds nothing but testnet ETH. `.env` is gitignored —
if a key ever does get committed, rotate it rather than just deleting the file,
because git history keeps it.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `EACCES ... spawnSync .../esbuild` | `noexec` mount — see the Level 2 box |
| `.venv/bin/pip: Permission denied` | Same. Put the venv on your home partition |
| `No deployment found at ...localhost.json` | Run `npm run deploy:local` first |
| `Firmware server is not answering on 8081` | Start `scenarios/00-start-server.sh` |
| `web3 is not installed` | Use the venv interpreter, or pass `--offline` |
| `Connect a wallet before publishing` | MetaMask not connected, or use demo mode |
| Port 8545 already in use | An old Hardhat node: `pkill -f "hardhat.*node"` |
