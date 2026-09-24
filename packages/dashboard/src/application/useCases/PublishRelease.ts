import { FirmwareVersion } from "../../domain";
import type { FirmwareHash } from "../../domain";
import type { FirmwareHasherPort } from "../ports/FirmwareHasherPort";
import type { ReleaseRegistryPort } from "../ports/ReleaseRegistryPort";

export interface PublishRequest {
  readonly model: string;
  readonly semver: string;
  readonly file: Blob;
  readonly locator: string;
}

export interface PublishResult {
  readonly transactionHash: string;
  readonly firmwareHash: FirmwareHash;
  readonly version: FirmwareVersion;
  readonly explorerUrl: string | null;
}

export class PublishRejected extends Error {}

/**
 * Hash a firmware file in the browser and publish its fingerprint on-chain.
 *
 * The monotonicity check is duplicated here on purpose. The contract is the
 * authority and will revert, but reverting costs gas and gives a cryptic error;
 * catching it in the use case turns a failed transaction into a clear message
 * before the wallet ever opens.
 */
export class PublishReleaseUseCase {
  constructor(
    private readonly registry: ReleaseRegistryPort,
    private readonly hasher: FirmwareHasherPort
  ) {}

  async execute(request: PublishRequest): Promise<PublishResult> {
    const version = FirmwareVersion.fromSemver(request.semver);

    if (!request.locator.trim()) {
      throw new PublishRejected(
        "A release needs a locator so devices know where to fetch the image."
      );
    }

    const latest = await this.registry.latestVersion(request.model);
    if (latest.isPublished && !version.isNewerThan(latest)) {
      throw new PublishRejected(
        `Version must be newer than the published ${latest}. The contract ` +
          `enforces strictly increasing versions, which is what makes a ` +
          `downgrade attack impossible.`
      );
    }

    const firmwareHash = await this.hasher.hash(request.file);

    const transactionHash = await this.registry.publish({
      model: request.model,
      version,
      firmwareHash,
      locator: request.locator.trim(),
    });

    return {
      transactionHash,
      firmwareHash,
      version,
      explorerUrl: this.registry.explorerUrlFor(transactionHash),
    };
  }
}
