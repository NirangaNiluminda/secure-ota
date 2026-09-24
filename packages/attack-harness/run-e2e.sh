#!/usr/bin/env bash
# End-to-end integration test across all four packages.
#
# Starts the untrusted firmware server, runs the control case and every attack
# against the deployed contract, and fails loudly if any defence misbehaves.
# This is the gate for Stage 3: if it is green, the demo works.
#
# Prerequisites, from packages/contracts:
#   npm run node                              # in another terminal
#   npm run deploy:local && npm run seed:local
#
# Then, from here:
#   PYTHON=/path/to/python-with-web3 ./run-e2e.sh

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/scenarios/_common.sh"

SERVER_PID=""
cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

serve_pristine

# Reuse a server that is already running — under Docker it is a sibling
# container sharing the document-root volume, and starting a second one here
# would serve different bytes than the one the ledger's locators point at.
if server_is_up; then
  note "using the firmware server already running at $SERVER_URL"
else
  "$PYTHON" "$HERE/src/firmware_server.py" --root "$SERVE_ROOT" --port "$SERVER_PORT" \
    >"$HERE/.serve/server.log" 2>&1 &
  SERVER_PID=$!

  for _ in $(seq 1 40); do
    server_is_up && break
    sleep 0.25
  done
fi
require_server

banner "SecureOTA end-to-end"
note "contract  $CONTRACT"
note "rpc       $RPC_URL"
note "server    http://127.0.0.1:$SERVER_PORT (untrusted)"

FAILED=0
for scenario in "$HERE"/scenarios/0[1-4]-*.sh; do
  if ! bash "$scenario"; then
    printf '%s%s  scenario failed: %s%s\n' "$RED" "$BOLD" "$(basename "$scenario")" "$RESET"
    FAILED=$((FAILED + 1))
  fi
done

if [[ $FAILED -eq 0 ]]; then
  printf '\n%s%s  ALL SCENARIOS PASSED — every defence held%s\n\n' "$GREEN" "$BOLD" "$RESET"
else
  printf '\n%s%s  %d SCENARIO(S) FAILED%s\n\n' "$RED" "$BOLD" "$FAILED" "$RESET"
fi

exit $FAILED
