#!/usr/bin/env bash
# Attack 3: install a release the manufacturer withdrew after a CVE.
#
# Today this is an advisory email most fleets never act on. Here the withdrawal
# is a ledger state change the device reads and enforces by itself, with no
# dependency on the vendor's servers still being reachable.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_server

banner "ATTACK — revoked release"

serve_pristine
reset_device 10200 "1.2.0"
step "Device is on v1.2.0. v1.3.0 was published, then withdrawn for CVE-2026-0001."

attack "Offering the device the withdrawn v1.3.0"
note "The image is genuine and its hash matches. It is simply not safe to run."

set +e
device update --version 1.3.0
EXIT=$?
set -e

[[ $EXIT -eq 1 ]] || fail "expected the device to refuse (exit 1), got exit $EXIT"
[[ "$(installed_version)" == "10200" ]] || fail "device installed a revoked release"

pass "revoked release refused on-device; still on v1.2.0"
