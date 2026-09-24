import { useCallback, useEffect, useMemo, useState } from "react";

import type { ReleaseTable as ReleaseTableModel } from "../application/useCases/ListReleases";
import type { WalletAccount } from "../application/ports/WalletPort";
import { DashboardContainer, readConfig } from "../composition/container";
import type { Release } from "../domain";
import { PublishForm } from "./components/PublishForm";
import { ReleaseTable } from "./components/ReleaseTable";
import { WalletBadge } from "./components/WalletBadge";

interface Notice {
  kind: "ok" | "error";
  text: string;
  link?: string | null;
}

function describe(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

export function App() {
  // Built once. Everything below receives ports, never implementations.
  const container = useMemo(() => new DashboardContainer(readConfig()), []);
  const { deviceModel, firmwareBaseUrl } = container.config;

  const [table, setTable] = useState<ReleaseTableModel | null>(null);
  const [account, setAccount] = useState<WalletAccount | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setTable(await container.listReleases.execute(deviceModel));
    } catch (error) {
      setNotice({ kind: "error", text: describe(error) });
    }
  }, [container, deviceModel]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    void container.wallet.currentAccount().then(setAccount);
    return container.wallet.onAccountChanged(setAccount);
  }, [container]);

  async function connect() {
    try {
      setAccount(await container.wallet.connect());
    } catch (error) {
      setNotice({ kind: "error", text: describe(error) });
    }
  }

  async function publish(input: {
    semver: string;
    file: File;
    locator: string;
  }) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await container.publishRelease.execute({
        model: deviceModel,
        ...input,
      });
      setNotice({
        kind: "ok",
        text: `Published ${result.version} — ${result.firmwareHash.hex}`,
        link: result.explorerUrl,
      });
      await refresh();
    } catch (error) {
      setNotice({ kind: "error", text: describe(error) });
    } finally {
      setBusy(false);
    }
  }

  async function revoke(release: Release) {
    const confirmed = window.confirm(
      `Revoke ${release.version}?\n\n` +
        `Every device will refuse to install it from now on, and this cannot ` +
        `be undone. Shipping a fix means publishing a new version.`
    );
    if (!confirmed) return;

    setBusy(true);
    setNotice(null);
    try {
      const result = await container.revokeRelease.execute(
        deviceModel,
        release.version.semver
      );
      setNotice({
        kind: "ok",
        text: `${release.version} revoked. Devices will now refuse it.`,
        link: result.explorerUrl,
      });
      await refresh();
    } catch (error) {
      setNotice({ kind: "error", text: describe(error) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="masthead">
        <div>
          <h1>SecureOTA — Manufacturer Console</h1>
          <div className="subtitle">
            {table?.source ?? container.registry.describeSource()} · model{" "}
            <span className="mono">{deviceModel}</span>
          </div>
        </div>
        <WalletBadge
          account={account}
          available={container.wallet.isAvailable()}
          demoMode={container.isDemoMode}
          onConnect={() => void connect()}
        />
      </header>

      {notice && (
        <div className={`notice ${notice.kind}`}>
          <span className="mono">{notice.text}</span>
          {notice.link && (
            <>
              {" — "}
              <a href={notice.link} target="_blank" rel="noreferrer">
                view transaction
              </a>
            </>
          )}
        </div>
      )}

      <PublishForm
        model={deviceModel}
        firmwareBaseUrl={firmwareBaseUrl}
        hasher={container.hasher}
        busy={busy}
        onPublish={publish}
      />

      <ReleaseTable
        releases={table?.releases ?? []}
        latestInstallable={table?.latestInstallable ?? null}
        busy={busy}
        onRevoke={(release) => void revoke(release)}
      />
    </div>
  );
}
