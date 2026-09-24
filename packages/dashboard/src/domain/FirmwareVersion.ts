/**
 * A release version, stored as the monotonic integer the contract uses.
 *
 * The encoding must match the device client and the seed script exactly, or the
 * three packages disagree about what "1.4.0" means. It is defined once here and
 * nowhere else in the dashboard.
 */

const MINOR_SCALE = 100;
const MAJOR_SCALE = 10_000;
const SEMVER = /^(\d+)\.(\d+)\.(\d+)$/;

export class InvalidFirmwareVersion extends Error {}

export class FirmwareVersion {
  private constructor(readonly code: number) {}

  /** `1.4.0` becomes `10400`. */
  static fromSemver(value: string): FirmwareVersion {
    const match = SEMVER.exec(value.trim());
    if (!match) {
      throw new InvalidFirmwareVersion(`not a semantic version: "${value}"`);
    }

    const [major, minor, patch] = match.slice(1, 4).map(Number);
    if (minor >= MINOR_SCALE || patch >= MINOR_SCALE) {
      throw new InvalidFirmwareVersion(
        "minor and patch components must each be below 100"
      );
    }

    return new FirmwareVersion(
      major * MAJOR_SCALE + minor * MINOR_SCALE + patch
    );
  }

  static fromCode(code: number | bigint): FirmwareVersion {
    const value = Number(code);
    if (!Number.isInteger(value) || value < 0) {
      throw new InvalidFirmwareVersion(`not a version code: ${code}`);
    }
    return new FirmwareVersion(value);
  }

  get semver(): string {
    const major = Math.floor(this.code / MAJOR_SCALE);
    const remainder = this.code % MAJOR_SCALE;
    return `${major}.${Math.floor(remainder / MINOR_SCALE)}.${
      remainder % MINOR_SCALE
    }`;
  }

  /** Zero is the contract's sentinel for "nothing published yet". */
  get isPublished(): boolean {
    return this.code > 0;
  }

  isNewerThan(other: FirmwareVersion): boolean {
    return this.code > other.code;
  }

  toString(): string {
    return `v${this.semver}`;
  }
}
