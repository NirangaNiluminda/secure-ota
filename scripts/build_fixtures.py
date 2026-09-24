#!/usr/bin/env python3
"""Generate the firmware binaries described by the shared fixture.

Run from the repository root::

    python3 scripts/build_fixtures.py

Writes one ``.bin`` per release and prints the SHA-256 the contract should be
seeded with. Keeping the bytes and the digests generated from a single source
means a fixture can never describe a file it does not match — the class of bug
that would otherwise waste an evening of integration debugging.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / (
    "packages/shared/fixtures/sample-releases.json"
)


def main() -> int:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    model = document["deviceModel"]

    print(f"model: {model}")
    print(f"fixture: {FIXTURE.relative_to(Path.cwd())}\n")

    for entry in document["releases"]:
        payload = entry["payload"].encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()

        target = FIXTURE.parent / entry["locator"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

        flag = "  [REVOKED]" if entry.get("revoked") else ""
        print(f"  v{entry['semver']:<8} {len(payload):>5} B  0x{digest}{flag}")
        print(f"             -> {target.relative_to(FIXTURE.parent)}")

    print("\nSeed the contract with these digests (scripts/seed.ts in contracts).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
