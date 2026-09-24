#!/usr/bin/env node
/**
 * Copy the frozen ABI from packages/shared into the dashboard's source tree.
 *
 * Vite will not import across the package boundary, so the dashboard keeps a
 * copy. A copy can drift, which is why check-layering.mjs verifies it still
 * matches the source of truth and fails the build if it does not.
 */

import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, "..", "..", "shared", "abi", "FirmwareRegistry.json");
const target = join(here, "..", "src", "infrastructure", "abi", "FirmwareRegistry.json");

mkdirSync(dirname(target), { recursive: true });
copyFileSync(source, target);

console.log(`synced ABI -> ${target}`);
