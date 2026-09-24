import type { DraftRelease, FirmwareVersion, Release } from "../../domain";

/**
 * Port: the on-chain release register.
 *
 * Implemented by EthersReleaseRegistry against a real contract, and by
 * DemoReleaseRegistry in memory so the UI can be built and shown without a
 * wallet. No component knows which one it is talking to.
 */
export interface ReleaseRegistryPort {
  /** Every release for a model, newest first. */
  listReleases(model: string): Promise<Release[]>;

  /** The highest published version, or a zero version if nothing is published. */
  latestVersion(model: string): Promise<FirmwareVersion>;

  /** Publish a release. Resolves with the transaction hash. */
  publish(draft: DraftRelease): Promise<string>;

  /** Withdraw a release. Resolves with the transaction hash. */
  revoke(model: string, version: FirmwareVersion): Promise<string>;

  /** A link to the transaction on a block explorer, when the network has one. */
  explorerUrlFor(transactionHash: string): string | null;

  /** Human-readable description of what this is connected to. */
  describeSource(): string;
}
