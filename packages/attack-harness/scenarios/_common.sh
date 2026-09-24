#!/usr/bin/env bash
# Shared setup for every scenario. Sourced, never run directly.
#
# Each scenario asserts its own expected outcome and exits non-zero if the
# defence did not behave, so the same script serves the live demo and CI. A
# defence that silently stopped working would otherwise be discovered on stage.

set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$HARNESS_DIR/../.." && pwd)"

# Override PYTHON to point at an interpreter that has web3 installed.
PYTHON="${PYTHON:-python3}"
RPC_URL="${RPC_URL:-http://127.0.0.1:8545}"
SERVER_PORT="${SERVER_PORT:-8081}"

SERVE_ROOT="$HARNESS_DIR/.serve/www"
STATE="$HARNESS_DIR/.serve/state.json"
SLOT="$HARNESS_DIR/.serve/slot"
FIXTURE_FIRMWARE="$REPO_ROOT/packages/shared/fixtures/firmware"
DEPLOYMENT="$REPO_ROOT/packages/contracts/deployments/localhost.json"

export PYTHONPATH="$REPO_ROOT/packages/device-client/src"

BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'
GREEN=$'\033[32m'; CYAN=$'\033[36m'; RESET=$'\033[0m'

banner()  { printf '\n%s=== %s ===%s\n\n' "$BOLD" "$1" "$RESET"; }
step()    { printf '%s  → %s%s\n' "$CYAN" "$1" "$RESET"; }
attack()  { printf '%s  ☠ %s%s\n' "$RED" "$1" "$RESET"; }
note()    { printf '%s    %s%s\n' "$DIM" "$1" "$RESET"; }
pass()    { printf '\n%s%s  PASS — %s%s\n\n' "$GREEN" "$BOLD" "$1" "$RESET"; }
fail()    { printf '\n%s%s  FAIL — %s%s\n\n' "$RED" "$BOLD" "$1" "$RESET"; exit 1; }

if [[ -z "${CONTRACT:-}" ]]; then
  if [[ ! -f "$DEPLOYMENT" ]]; then
    echo "No deployment found at $DEPLOYMENT" >&2
    echo "Run, from packages/contracts:" >&2
    echo "  npm run node      # in another terminal" >&2
    echo "  npm run deploy:local && npm run seed:local" >&2
    exit 2
  fi
  CONTRACT="$("$PYTHON" -c \
    "import json,sys; print(json.load(open(sys.argv[1]))['address'])" "$DEPLOYMENT")"
fi

# Restore the document root to the genuine firmware the manufacturer published.
serve_pristine() {
  mkdir -p "$SERVE_ROOT/firmware"
  cp "$FIXTURE_FIRMWARE"/*.bin "$SERVE_ROOT/firmware/"
}

# Put the device back on a known firmware version. Writing the state file
# directly is itself a reminder that on real hardware this belongs somewhere an
# attacker cannot reach.
reset_device() {
  mkdir -p "$(dirname "$STATE")"
  printf '{"model":"RUH-SENSOR-01","installedVersion":%s,"installedSemver":"%s","lastCheckedAt":null}\n' \
    "$1" "$2" > "$STATE"
  rm -rf "$SLOT"
}

device() {
  "$PYTHON" -m secure_ota_device.cli.main \
    --contract "$CONTRACT" --rpc-url "$RPC_URL" \
    --state "$STATE" --slot "$SLOT" "$@"
}

require_server() {
  if ! curl -fsS -o /dev/null "http://127.0.0.1:$SERVER_PORT/firmware/" 2>/dev/null; then
    echo "Firmware server is not answering on port $SERVER_PORT." >&2
    echo "Start it with: ./scenarios/00-start-server.sh" >&2
    exit 2
  fi
}

installed_version() {
  "$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1]))['installedVersion'])" "$STATE"
}
