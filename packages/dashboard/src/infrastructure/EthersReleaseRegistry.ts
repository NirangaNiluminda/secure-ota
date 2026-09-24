import { Contract, JsonRpcProvider } from "ethers";

import { FirmwareHash, FirmwareVersion } from "../domain";
import type { DraftRelease, Release } from "../domain";
import type { ReleaseRegistryPort } from "../application/ports/ReleaseRegistryPort";
import type { BrowserWallet } from "./BrowserWallet";
import registrySpec from "./abi/FirmwareRegistry.json";

const EXPLORERS: Record<number, string> = {
  1: "https://etherscan.io",
  11155111: "https://sepolia.etherscan.io",
};

/**
 * Adapter: the FirmwareRegistry contract, reached over JSON-RPC.
 *
 * The only file in the dashboard that imports ethers. Everything above it works
 * in domain types, so `npm run check:layering` can assert that no component
 * reaches past this boundary.
 */
export class EthersReleaseRegistry implements ReleaseRegistryPort {
  private readonly readProvider: JsonRpcProvider;

  /**
   * Takes a URL rather than a constructed provider, and asks the wallet adapter
   * for a signer only when one is needed. That keeps every `ethers` symbol
   * inside this layer — the composition root wires plain configuration, and
   * `npm run check:layering` can enforce that.
   */
  constructor(
    private readonly address: string,
    rpcUrl: string,
    private readonly chainId: number,
    private readonly wallet: BrowserWallet
  ) {
    this.readProvider = new JsonRpcProvider(rpcUrl);
  }

  describeSource(): string {
    return `FirmwareRegistry @ ${this.address} (chain ${this.chainId})`;
  }

  explorerUrlFor(transactionHash: string): string | null {
    const base = EXPLORERS[this.chainId];
    return base ? `${base}/tx/${transactionHash}` : null;
  }

  async latestVersion(model: string): Promise<FirmwareVersion> {
    const code: bigint = await this.reader().latestVersion(model);
    return FirmwareVersion.fromCode(code);
  }

  async listReleases(model: string): Promise<Release[]> {
    const contract = this.reader();

    // Discover which versions exist from the event log, then read each one back
    // through releaseAt. The log says what happened; the contract state says
    // what is true now — in particular whether a release has since been
    // revoked, which a ReleasePublished event cannot know.
    const published = await contract.queryFilter(
      contract.filters.ReleasePublished(model)
    );

    const versions = [
      ...new Set(
        published
          .map((event) => ("args" in event ? Number(event.args?.[1] ?? 0) : 0))
          .filter((code) => code > 0)
      ),
    ];

    const releases = await Promise.all(
      versions.map(async (code) => this.readRelease(model, code))
    );
    return releases;
  }

  async publish(draft: DraftRelease): Promise<string> {
    const contract = await this.writer();
    const transaction = await contract.publishRelease(
      draft.model,
      draft.version.code,
      draft.firmwareHash.hex,
      draft.locator
    );
    await transaction.wait();
    return transaction.hash;
  }

  async revoke(model: string, version: FirmwareVersion): Promise<string> {
    const contract = await this.writer();
    const transaction = await contract.revokeRelease(model, version.code);
    await transaction.wait();
    return transaction.hash;
  }

  // -- internals ---------------------------------------------------------

  private reader(): Contract {
    return new Contract(this.address, registrySpec.abi, this.readProvider);
  }

  private async writer(): Promise<Contract> {
    const provider = this.wallet.provider();
    if (!provider) {
      throw new Error("Connect a wallet before publishing or revoking.");
    }
    const signer = await provider.getSigner();
    return new Contract(this.address, registrySpec.abi, signer);
  }

  /** Translate the ABI tuple into domain types — the anti-corruption boundary. */
  private async readRelease(model: string, code: number): Promise<Release> {
    const raw = await this.reader().releaseAt(model, code);
    return {
      model,
      version: FirmwareVersion.fromCode(raw.version),
      firmwareHash: FirmwareHash.fromHex(raw.firmwareHash),
      locator: String(raw.locator),
      publishedAt: new Date(Number(raw.publishedAt) * 1000),
      revoked: Boolean(raw.revoked),
    };
  }
}
