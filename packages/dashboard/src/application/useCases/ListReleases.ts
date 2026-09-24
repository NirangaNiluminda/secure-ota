import { byNewestFirst } from "../../domain";
import type { Release } from "../../domain";
import type { ReleaseRegistryPort } from "../ports/ReleaseRegistryPort";

export interface ReleaseTable {
  readonly releases: Release[];
  readonly source: string;
  readonly latestInstallable: Release | null;
}

/** Read the release history for a model, in the order a table should show it. */
export class ListReleasesUseCase {
  constructor(private readonly registry: ReleaseRegistryPort) {}

  async execute(model: string): Promise<ReleaseTable> {
    const releases = (await this.registry.listReleases(model)).sort(
      byNewestFirst
    );

    // What a device would actually accept right now: the newest release that
    // has not been withdrawn. Showing it makes the effect of a revocation
    // visible immediately, which is the point of the revocation demo.
    const latestInstallable =
      releases.find((release) => !release.revoked) ?? null;

    return {
      releases,
      source: this.registry.describeSource(),
      latestInstallable,
    };
  }
}
