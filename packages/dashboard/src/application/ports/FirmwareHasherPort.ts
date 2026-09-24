import type { FirmwareHash } from "../../domain";

/**
 * Port: computing a firmware image's digest.
 *
 * Deliberately a port rather than a bare function call, because *where* hashing
 * happens is a security property, not an implementation detail. The browser
 * implementation never transmits the file — only its fingerprint leaves the
 * machine, which is the claim the whole project rests on.
 */
export interface FirmwareHasherPort {
  hash(file: Blob): Promise<FirmwareHash>;
}
