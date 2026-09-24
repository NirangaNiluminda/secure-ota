#!/usr/bin/env bash
# Control case: an honest update succeeds.
#
# This matters as much as the attacks. Without it, the audience cannot tell a
# working defence from a device that refuses everything.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_server

banner "CONTROL — an honest update"

serve_pristine
reset_device 10200 "1.2.0"
step "Device is on v1.2.0. The server holds the genuine v1.4.0 image."
step "Nobody is interfering."

set +e
device update
EXIT=$?
set -e

[[ $EXIT -eq 0 ]] || fail "expected the update to succeed, got exit $EXIT"
[[ "$(installed_version)" == "10400" ]] || fail "device did not move to v1.4.0"

pass "verified image installed; device is on v1.4.0"
