/**
 * A SHA-256 digest of a firmware binary.
 *
 * The dashboard never uploads a file to learn its hash — it computes the digest
 * in the browser and sends only the fingerprint. That is the whole scheme in one
 * gesture, and it is worth saying out loud during the demo.
 */

const HEX64 = /^0x[0-9a-f]{64}$/;

export class InvalidFirmwareHash extends Error {}

export class FirmwareHash {
  private constructor(readonly hex: string) {}

  static fromHex(value: string): FirmwareHash {
    const normalised = value.trim().toLowerCase();
    const prefixed = normalised.startsWith("0x")
      ? normalised
      : `0x${normalised}`;

    if (!HEX64.test(prefixed)) {
      throw new InvalidFirmwareHash(`not a 32-byte hex digest: "${value}"`);
    }
    return new FirmwareHash(prefixed);
  }

  static fromBytes(digest: ArrayBuffer | Uint8Array): FirmwareHash {
    const bytes =
      digest instanceof Uint8Array ? digest : new Uint8Array(digest);
    if (bytes.length !== 32) {
      throw new InvalidFirmwareHash("a firmware hash must be exactly 32 bytes");
    }
    const hex = Array.from(bytes, (byte) =>
      byte.toString(16).padStart(2, "0")
    ).join("");
    return new FirmwareHash(`0x${hex}`);
  }

  /** Abbreviated for tables; the full value is always available via `hex`. */
  get short(): string {
    return `${this.hex.slice(0, 10)}…${this.hex.slice(-6)}`;
  }

  equals(other: FirmwareHash): boolean {
    return this.hex === other.hex;
  }

  toString(): string {
    return this.hex;
  }
}
