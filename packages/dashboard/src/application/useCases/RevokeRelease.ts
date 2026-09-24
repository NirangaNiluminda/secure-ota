import { FirmwareVersion } from "../../domain";
import type { ReleaseRegistryPort } from "../ports/ReleaseRegistryPort";

export interface RevokeResult {
  readonly transactionHash: string;
  readonly explorerUrl: string | null;
}

/**
 * Withdraw a release after a vulnerability is disclosed.
 *
 * Irreversible, and the UI says so before asking for a signature. Today the
 * equivalent is an advisory email most fleets never act on; here every device
 * reads the withdrawal and enforces it by itself.
 */
export class RevokeReleaseUseCase {
  constructor(private readonly registry: ReleaseRegistryPort) {}

  async execute(model: string, semver: string): Promise<RevokeResult> {
    const version = FirmwareVersion.fromSemver(semver);
    const transactionHash = await this.registry.revoke(model, version);

    return {
      transactionHash,
      explorerUrl: this.registry.explorerUrlFor(transactionHash),
    };
  }
}
