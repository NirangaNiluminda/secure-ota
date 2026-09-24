# Running SecureOTA

Three levels, depending on how much you need. Start at level 1 — it needs
nothing installed and still shows every defence working.

If `npm run` gives you **`sh: 1: hardhat: Permission denied`**, skip to
[Docker](#docker--the-whole-stack-in-containers) or read
[why that happens](#why-npm-run-fails-on-an-ntfs-drive) first.

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

## Docker — the whole stack in containers

The most reliable path, and the one that makes all four members' environments
identical. It also sidesteps the NTFS execute-bit problem entirely, because the
dependency trees live on named volumes inside the containers.

```bash
docker compose build                              # first time only

docker compose up -d chain firmware dashboard     # start the stack
docker compose run --rm deployer                  # deploy + seed the registry
docker compose run --rm device bash run-e2e.sh    # every defence, end to end
```

Ports on the host: **8545** chain · **8081** firmware server · **5173** dashboard.

Individual scenarios, for the live demo:

```bash
docker compose run --rm device bash scenarios/01-happy-path.sh
docker compose run --rm device bash scenarios/02-tampered-binary.sh
docker compose run --rm device bash scenarios/03-rollback.sh
docker compose run --rm device bash scenarios/04-revoked-release.sh
```

The Python test suite:

```bash
docker compose run --rm tests
```

Watch the firmware server's log while attacking — it prints the SHA-256 of
everything it serves, so you can see the digest change the moment a file is
tampered with:

```bash
docker compose logs -f firmware
```

Tear down with `docker compose down`, or `docker compose down -v` to also drop
the dependency volumes and start clean.

### How it is wired

| Service | What it is | Notes |
|---|---|---|
| `chain` | Hardhat node | healthchecked, so `deployer` waits for it |
| `deployer` | one-shot deploy + seed | locators point at `http://firmware:8081/`, not localhost, because the device container has to resolve them |
| `firmware` | the untrusted server | shares its document root with `device` via a volume, so the attacker tampers with exactly the bytes being served |
| `dashboard` | Vite dev server | set `VITE_CONTRACT_ADDRESS` to leave demo mode |
| `device` | the device client and the attacker | `profiles: ["tools"]`, so it runs on demand rather than with `up` |

The source tree is bind-mounted read-write, so edits on the host take effect
immediately and `deployments/localhost.json` is written back where the host can
read it.

---

## Why `npm run` fails on an NTFS drive

npm scripts invoke `node_modules/.bin/<tool>`, a shebang launcher that needs the
Unix execute bit. This repository's drive is mounted by the desktop's automounter
as `fuseblk` with `user_id=0`, and **`chmod +x` on it silently does nothing** —
NTFS through that mount cannot carry the bit at all. So `npm run node` dies with
`sh: 1: hardhat: Permission denied`.

Three ways out, in order of preference:

**1. Use Docker** (above). Nothing to configure, and everyone gets the same
environment.

**2. Invoke the tool through node directly.** Works immediately, no setup:

```bash
cd packages/contracts
node node_modules/hardhat/internal/cli/bootstrap.js node
node node_modules/hardhat/internal/cli/bootstrap.js test
node node_modules/hardhat/internal/cli/bootstrap.js run scripts/deploy.ts --network localhost

cd packages/dashboard
node node_modules/typescript/lib/tsc.js --noEmit
node node_modules/vite/bin/vite.js build
```

`node` is the executable here, and it merely *reads* the `.js` file, so no
execute bit is needed on anything in `node_modules`.

**3. Fix the mount.** Permanent, but needs `sudo` and a careful edit. There is
already an fstab entry for this drive, but it is not the one in effect — the
desktop automounted the drive first. The entry also specifies `fmask=133`, which
yields `644` on every file, i.e. no execute bit. Change it to `fmask=022`:

```bash
sudo cp /etc/fstab /etc/fstab.backup          # always back it up first
sudo nano /etc/fstab                          # change fmask=133 to fmask=022

sudo umount /media/niranga/Engineering        # close all programs using it first
sudo mount /media/niranga/Engineering
findmnt -no OPTIONS --target /media/niranga/Engineering   # confirm
```

The existing entry has `nofail`, so a mistake will not stop the machine booting.
Verify with `ls -l packages/contracts/node_modules/.bin/hardhat` — you want to
see `x` bits. After this, plain `npm run node` works.

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
| Port 8545 already in use | An old Hardhat node: `pkill -f "hardhat.*node"`, or `docker compose down` |
| `sh: 1: hardhat: Permission denied` | NTFS execute bit — see [above](#why-npm-run-fails-on-an-ntfs-drive) |
| Docker build: `npm error EIDLETIMEOUT` | Slow link. The Dockerfile already raises npm's timeouts and retries; just run `docker compose build` again — completed layers are cached |
| Docker build: `failed to resolve source metadata` | Transient registry hiccup. `docker pull node:20-bookworm-slim` then rebuild |
| Docker: device cannot reach the firmware server | Start it first: `docker compose up -d firmware`. Inside compose the host is `firmware`, not `127.0.0.1` — `SERVER_HOST` handles that |
| Docker: stale dependencies after a package.json change | `docker compose build --no-cache` and `docker compose down -v` |
