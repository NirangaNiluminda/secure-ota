/** The connected signing account, if any. */
export interface WalletAccount {
  readonly address: string;
  readonly chainId: number;
}

/**
 * Port: the signer.
 *
 * Abstracted so swapping MetaMask for WalletConnect, or for a read-only demo
 * mode, touches one adapter rather than every component that shows an address.
 */
export interface WalletPort {
  connect(): Promise<WalletAccount>;
  currentAccount(): Promise<WalletAccount | null>;
  isAvailable(): boolean;
  onAccountChanged(listener: (account: WalletAccount | null) => void): () => void;
}
