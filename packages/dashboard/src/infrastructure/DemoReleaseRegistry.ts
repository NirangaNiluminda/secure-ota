import { FirmwareHash, FirmwareVersion } from "../domain";
import type { DraftRelease, Release } from "../domain";
import type { ReleaseRegistryPort } from "../application/ports/ReleaseRegistryPort";

/**
 * Adapter: an in-memory registry.
 *
 * Not a test double. It is what let the UI be built and demonstrated before the
 * contract was deployed, and it is the fallback if no wallet is installed on the
 * machine used to present. It enforces the same monotonicity and one-way
 * revocation rules as the contract, so demo mode cannot teach the audience
 * something the real system would not do.
 */
export class DemoReleaseRegistry implements ReleaseRegistryPort {
  private readonly releases = new Map<string, Release[]>();

  constructor(seed: Release[] = []) {
    for (const release of seed) {
      this.bucket(release.model).push(release);
    }
  }

  describeSource(): string {
    return "in-memory demo registry (no chain)";
  }

  explorerUrlFor(): string | null {
    return null;
  }

  async listReleases(model: string): Promise<Release[]> {
    return [...this.bucket(model)];
  }

  async latestVersion(model: string): Promise<FirmwareVersion> {
    const codes = this.bucket(model).map((release) => release.version.code);
    return FirmwareVersion.fromCode(codes.length ? Math.max(...codes) : 0);
  }

  async publish(draft: DraftRelease): Promise<string> {
    const latest = await this.latestVersion(draft.model);
    if (latest.isPublished && !draft.version.isNewerThan(latest)) {
      throw new Error(`version must exceed the published ${latest}`);
    }

    this.bucket(draft.model).push({
      ...draft,
      publishedAt: new Date(),
      revoked: false,
    });

    return `0xdemo${Date.now().toString(16).padStart(60, "0")}`;
  }

  async revoke(model: string, version: FirmwareVersion): Promise<string> {
    const bucket = this.bucket(model);
    const index = bucket.findIndex(
      (release) => release.version.code === version.code
    );
    if (index < 0) throw new Error(`unknown release ${version}`);
    if (bucket[index].revoked) throw new Error(`${version} is already revoked`);

    bucket[index] = { ...bucket[index], revoked: true };
    return `0xdemo${Date.now().toString(16).padStart(60, "0")}`;
  }

  private bucket(model: string): Release[] {
    let existing = this.releases.get(model);
    if (!existing) {
      existing = [];
      this.releases.set(model, existing);
    }
    return existing;
  }
}

/** The same three releases the other packages use, so demo mode matches. */
export function demoSeed(model: string): Release[] {
  const make = (
    semver: string,
    hex: string,
    revoked: boolean,
    day: number
  ): Release => ({
    model,
    version: FirmwareVersion.fromSemver(semver),
    firmwareHash: FirmwareHash.fromHex(hex),
    locator: `http://127.0.0.1:8081/firmware/${model}-${semver}.bin`,
    publishedAt: new Date(Date.UTC(2026, 7, day)),
    revoked,
  });

  return [
    make(
      "1.2.0",
      "0x415eb097d5ca3a2f5792c9ddbd2fb11e519e71f918b5a3582b79e67be40ee92e",
      false,
      1
    ),
    make(
      "1.3.0",
      "0x099a9a42bfd338af4e3821a615c5cafa3ace2785d00ef2968e8faded9261f859",
      true,
      27
    ),
    make(
      "1.4.0",
      "0x063462b7eff41533f04c0cac832596c3085632404d8e8c1f09e0b8653981b310",
      false,
      31
    ),
  ];
}
