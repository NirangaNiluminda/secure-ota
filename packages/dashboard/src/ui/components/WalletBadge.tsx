import type { WalletAccount } from "../../application/ports/WalletPort";

interface Props {
  account: WalletAccount | null;
  available: boolean;
  demoMode: boolean;
  onConnect: () => void;
}

/** Presentational only — it receives an account, it does not know what a wallet is. */
export function WalletBadge({ account, available, demoMode, onConnect }: Props) {
  if (demoMode) {
    return (
      <div className="wallet">
        <span className="badge demo">demo mode</span>
        <span>no contract configured — using an in-memory registry</span>
      </div>
    );
  }

  if (!available) {
    return (
      <div className="wallet">
        <span className="badge revoked">no wallet</span>
        <span>install MetaMask to publish</span>
      </div>
    );
  }

  if (!account) {
    return (
      <div className="wallet">
        <button className="ghost" onClick={onConnect}>
          Connect wallet
        </button>
      </div>
    );
  }

  return (
    <div className="wallet">
      <span className="badge live">connected</span>
      <span className="mono">
        {account.address.slice(0, 6)}…{account.address.slice(-4)}
      </span>
      <span>chain {account.chainId}</span>
    </div>
  );
}
