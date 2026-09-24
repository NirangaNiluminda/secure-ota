import { BrowserProvider } from "ethers";

import type { WalletAccount, WalletPort } from "../application/ports/WalletPort";

interface Eip1193Provider {
  request(args: { method: string; params?: unknown[] }): Promise<unknown>;
  on?(event: string, listener: (...args: unknown[]) => void): void;
  removeListener?(event: string, listener: (...args: unknown[]) => void): void;
}

declare global {
  interface Window {
    ethereum?: Eip1193Provider;
  }
}

/**
 * Adapter: an EIP-1193 browser wallet such as MetaMask.
 *
 * Typed against the EIP-1193 interface rather than MetaMask specifically, so any
 * conforming wallet works and the port stays honest about what is required.
 */
export class BrowserWallet implements WalletPort {
  isAvailable(): boolean {
    return typeof window !== "undefined" && Boolean(window.ethereum);
  }

  provider(): BrowserProvider | null {
    return this.isAvailable() ? new BrowserProvider(window.ethereum!) : null;
  }

  async connect(): Promise<WalletAccount> {
    const provider = this.provider();
    if (!provider) {
      throw new Error(
        "No browser wallet detected. Install MetaMask, or run the dashboard in demo mode."
      );
    }

    const signer = await provider.getSigner();
    const network = await provider.getNetwork();
    return { address: await signer.getAddress(), chainId: Number(network.chainId) };
  }

  async currentAccount(): Promise<WalletAccount | null> {
    const provider = this.provider();
    if (!provider) return null;

    // eth_accounts does not prompt, so this can run on mount without throwing
    // a wallet popup at someone who only wanted to read the release table.
    const accounts = (await window.ethereum!.request({
      method: "eth_accounts",
    })) as string[];
    if (!accounts?.length) return null;

    const network = await provider.getNetwork();
    return { address: accounts[0], chainId: Number(network.chainId) };
  }

  onAccountChanged(
    listener: (account: WalletAccount | null) => void
  ): () => void {
    if (!this.isAvailable() || !window.ethereum?.on) return () => {};

    const handler = () => {
      void this.currentAccount().then(listener);
    };

    window.ethereum.on("accountsChanged", handler);
    window.ethereum.on("chainChanged", handler);

    return () => {
      window.ethereum?.removeListener?.("accountsChanged", handler);
      window.ethereum?.removeListener?.("chainChanged", handler);
    };
  }
}
