import type { FirmwareHash } from "./FirmwareHash";
import type { FirmwareVersion } from "./FirmwareVersion";

/**
 * A release record as published on-chain.
 *
 * Immutable, like its Python counterpart in the device client: a release is a
 * claim the manufacturer made at a point in time, and the only mutation the
 * contract permits afterwards is the one-way revocation flag.
 */
export interface Release {
  readonly model: string;
  readonly version: FirmwareVersion;
  readonly firmwareHash: FirmwareHash;
  readonly locator: string;
  readonly publishedAt: Date;
  readonly revoked: boolean;
}

/** A release the manufacturer is about to publish. */
export interface DraftRelease {
  readonly model: string;
  readonly version: FirmwareVersion;
  readonly firmwareHash: FirmwareHash;
  readonly locator: string;
}

export function isInstallable(release: Release): boolean {
  return !release.revoked;
}

/** Newest first — the order a release table should show. */
export function byNewestFirst(a: Release, b: Release): number {
  return b.version.code - a.version.code;
}
