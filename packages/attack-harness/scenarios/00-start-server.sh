#!/usr/bin/env bash
# Start the untrusted firmware server in the foreground.
#
# Run this in its own terminal during the demo so the audience can watch the
# served digest change the instant the attacker swaps a file.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

serve_pristine

banner "Untrusted firmware server"
note "This stands in for the vendor CDN. SecureOTA does not trust it."
note "Ctrl-C to stop."

exec "$PYTHON" "$HARNESS_DIR/src/firmware_server.py" \
  --root "$SERVE_ROOT" --port "$SERVER_PORT"
