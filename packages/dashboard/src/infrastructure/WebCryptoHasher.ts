import { FirmwareHash } from "../domain";
import type { FirmwareHasherPort } from "../application/ports/FirmwareHasherPort";

/**
 * Computes a firmware digest with the browser's SubtleCrypto.
 *
 * The file never leaves the machine. Only the 32-byte fingerprint is sent, and
 * only to the blockchain — which is the difference between SecureOTA and an
 * ordinary upload-and-trust-the-server pipeline.
 */
export class WebCryptoHasher implements FirmwareHasherPort {
  async hash(file: Blob): Promise<FirmwareHash> {
    const buffer = await file.arrayBuffer();
    const digest = await crypto.subtle.digest("SHA-256", buffer);
    return FirmwareHash.fromBytes(digest);
  }
}
