#!/usr/bin/env python3
"""The untrusted firmware server.

Stands in for the vendor's CDN or an IPFS gateway: infrastructure SecureOTA
deliberately does not trust. It serves whatever bytes are in its document root,
including bytes an attacker has swapped, which is exactly the point — the device
is supposed to catch that, and this is what lets us prove it does.

    python3 src/firmware_server.py --root .serve/www --port 8081

Every request is logged with the SHA-256 of what was actually served, so during
the demo the audience can watch the served digest change the moment the attacker
tampers with a file.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_GREEN = "\033[32m"
_RED = "\033[31m"
_DIM = "\033[2m"
_RESET = "\033[0m"


class FirmwareRequestHandler(SimpleHTTPRequestHandler):
    """Serves files and reports the digest of each one it hands out."""

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        """Suppress the default one-line-per-request noise."""

    def do_GET(self) -> None:  # noqa: N802 - name fixed by the base class
        served = Path(self.translate_path(self.path))
        super().do_GET()

        if not served.is_file():
            print(f"{_RED}  404  {self.path}{_RESET}", file=sys.stderr, flush=True)
            return

        payload = served.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        print(
            f"{_DIM}  200  {self.path}  {len(payload)}B  "
            f"sha256={_RESET}{_GREEN}0x{digest[:8]}…{digest[-6:]}{_RESET}",
            file=sys.stderr,
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="SecureOTA untrusted firmware server")
    parser.add_argument("--root", type=Path, required=True, help="document root")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    handler = partial(FirmwareRequestHandler, directory=str(root))
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print(f"serving {root}", file=sys.stderr)
    print(
        f"on http://{args.host}:{args.port}/  (untrusted by design)\n",
        file=sys.stderr,
        flush=True,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
