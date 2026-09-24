#!/usr/bin/env bash
# Attack 1: a compromised CDN or a network MITM swaps the firmware image.
#
# The headline scenario. The ledger is untouched and the attacker controls only
# the bytes, which is precisely the situation SecureOTA is built for.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_server

banner "ATTACK — tampered binary"

serve_pristine
reset_device 10200 "1.2.0"
step "Device is on v1.2.0. The ledger says v1.4.0 is available."

TARGET="$SERVE_ROOT/firmware/RUH-SENSOR-01-1.4.0.bin"
attack "Replacing the served v1.4.0 image with an implant"
printf 'MALICIOUS-IMPLANT\nmodel=RUH-SENSOR-01\nversion=1.4.0\nbackdoor=enabled\n' > "$TARGET"
note "The vendor's own filename and version. Only the bytes changed."

set +e
device update
EXIT=$?
set -e

[[ $EXIT -eq 1 ]] || fail "expected the device to refuse (exit 1), got exit $EXIT"
[[ "$(installed_version)" == "10200" ]] || fail "device firmware changed despite refusing"

serve_pristine
pass "implant rejected on hash mismatch; device still on v1.2.0"
