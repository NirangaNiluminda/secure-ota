#!/usr/bin/env node
/**
 * Enforce the dashboard's architecture, the way the device client's
 * test_architecture.py enforces its own.
 *
 * Two rules, both of which would otherwise decay silently:
 *
 *   1. No UI component, use case or domain type may import ethers. Only
 *      `infrastructure/` may. The moment a component reaches for a provider,
 *      the UI stops being testable and swapping wallets becomes a refactor.
 *
 *   2. The vendored ABI must still match packages/shared. A stale copy is the
 *      exact failure the frozen seam exists to prevent.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "src");

const FORBIDDEN = /from\s+["']ethers["']|require\(["']ethers["']\)/;
const ALLOWED_PREFIX = join(src, "infrastructure");

function walk(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const full = join(directory, entry);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

const failures = [];

for (const file of walk(src)) {
  if (!/\.(ts|tsx)$/.test(file)) continue;
  if (file.startsWith(ALLOWED_PREFIX)) continue;

  if (FORBIDDEN.test(readFileSync(file, "utf8"))) {
    failures.push(
      `${relative(src, file)} imports ethers directly; go through a port instead`
    );
  }
}

const shared = join(here, "..", "..", "shared", "abi", "FirmwareRegistry.json");
const vendored = join(src, "infrastructure", "abi", "FirmwareRegistry.json");

try {
  const a = JSON.parse(readFileSync(shared, "utf8"));
  const b = JSON.parse(readFileSync(vendored, "utf8"));
  if (JSON.stringify(a.abi) !== JSON.stringify(b.abi)) {
    failures.push(
      "the vendored ABI has drifted from packages/shared — run `node scripts/sync-abi.mjs`"
    );
  }
  if (a.specVersion !== b.specVersion) {
    failures.push(
      `ABI specVersion mismatch: shared ${a.specVersion}, vendored ${b.specVersion}`
    );
  }
} catch (error) {
  failures.push(`could not compare ABIs: ${error.message}`);
}

if (failures.length > 0) {
  console.error("\nLayering check failed:\n");
  for (const failure of failures) console.error(`  ✗ ${failure}`);
  console.error("");
  process.exit(1);
}

console.log("✓ layering intact: ethers confined to infrastructure, ABI in sync");
