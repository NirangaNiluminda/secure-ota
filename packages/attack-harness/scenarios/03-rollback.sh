#!/usr/bin/env bash
# Attack 2: downgrade to a genuine but known-vulnerable release.
#
# The attack a signature check cannot see. Every byte of v1.2.0 is authentic and
# correctly signed by the manufacturer — it is simply the version whose
# vulnerability is now public. Only the version ordering exposes it.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_server

banner "ATTACK — rollback to a vulnerable release"

serve_pristine
reset_device 10400 "1.4.0"
step "Device is on the current v1.4.0."

attack "Steering the device at v1.2.0 — genuine bytes, public CVE"
note "A hostile RPC endpoint or proxy pinning the device to an old release."

set +e
device update --version 1.2.0
EXIT=$?
set -e

[[ $EXIT -eq 1 ]] || fail "expected the device to refuse (exit 1), got exit $EXIT"
[[ "$(installed_version)" == "10400" ]] || fail "device was downgraded"

pass "downgrade blocked before a single byte was downloaded; still on v1.4.0"
