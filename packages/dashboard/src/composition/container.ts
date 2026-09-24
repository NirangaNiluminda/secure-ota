import { ListReleasesUseCase } from "../application/useCases/ListReleases";
import { PublishReleaseUseCase } from "../application/useCases/PublishRelease";
import { RevokeReleaseUseCase } from "../application/useCases/RevokeRelease";
import type { FirmwareHasherPort } from "../application/ports/FirmwareHasherPort";
import type { ReleaseRegistryPort } from "../application/ports/ReleaseRegistryPort";
import type { WalletPort } from "../application/ports/WalletPort";
import { BrowserWallet } from "../infrastructure/BrowserWallet";
import { DemoReleaseRegistry, demoSeed } from "../infrastructure/DemoReleaseRegistry";
import { EthersReleaseRegistry } from "../infrastructure/EthersReleaseRegistry";
import { WebCryptoHasher } from "../infrastructure/WebCryptoHasher";

export interface DashboardConfig {
  readonly contractAddress: string;
  readonly rpcUrl: string;
  readonly chainId: number;
  readonly deviceModel: string;
  readonly firmwareBaseUrl: string;
}

export function readConfig(): DashboardConfig {
  const env = import.meta.env;
  return {
    contractAddress: env.VITE_CONTRACT_ADDRESS ?? "",
    rpcUrl: env.VITE_RPC_URL ?? "http://127.0.0.1:8545",
    chainId: Number(env.VITE_CHAIN_ID ?? 31337),
    deviceModel: env.VITE_DEVICE_MODEL ?? "RUH-SENSOR-01",
    firmwareBaseUrl:
      env.VITE_FIRMWARE_BASE_URL ?? "http://127.0.0.1:8081/firmware/",
  };
}

/**
 * The composition root.
 *
 * The one place where abstractions meet implementations, exactly as in the
 * device client. Falling back to the in-memory registry when no contract is
 * configured is what lets the UI be developed, and presented, without a chain —
 * and no component can tell the difference.
 */
export class DashboardContainer {
  readonly wallet: WalletPort;
  readonly registry: ReleaseRegistryPort;
  readonly isDemoMode: boolean;

  /** Exposed so the form can show a digest before anything is signed. The UI
   *  depends on the port, never on SubtleCrypto directly. */
  readonly hasher: FirmwareHasherPort;

  readonly publishRelease: PublishReleaseUseCase;
  readonly revokeRelease: RevokeReleaseUseCase;
  readonly listReleases: ListReleasesUseCase;

  constructor(readonly config: DashboardConfig) {
    const wallet = new BrowserWallet();
    this.wallet = wallet;

    this.isDemoMode = !config.contractAddress;
    this.registry = this.isDemoMode
      ? new DemoReleaseRegistry(demoSeed(config.deviceModel))
      : new EthersReleaseRegistry(
          config.contractAddress,
          config.rpcUrl,
          config.chainId,
          wallet
        );

    this.hasher = new WebCryptoHasher();
    this.publishRelease = new PublishReleaseUseCase(this.registry, this.hasher);
    this.revokeRelease = new RevokeReleaseUseCase(this.registry);
    this.listReleases = new ListReleasesUseCase(this.registry);
  }
}
