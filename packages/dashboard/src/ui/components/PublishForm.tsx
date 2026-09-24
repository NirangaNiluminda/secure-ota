import { useState } from "react";

import type { FirmwareHash } from "../../domain";
import type { FirmwareHasherPort } from "../../application/ports/FirmwareHasherPort";

interface Props {
  model: string;
  firmwareBaseUrl: string;
  hasher: FirmwareHasherPort;
  busy: boolean;
  onPublish: (input: {
    semver: string;
    file: File;
    locator: string;
  }) => Promise<void>;
}

/**
 * Publish panel.
 *
 * The digest is computed the moment a file is chosen, before anything is
 * signed, and shown at full length. That is the beat of the demo worth pausing
 * on: the audience sees the fingerprint here, then sees the same value land on
 * Etherscan, then sees the device reject anything that does not match it.
 */
export function PublishForm({
  model,
  firmwareBaseUrl,
  hasher,
  busy,
  onPublish,
}: Props) {
  const [semver, setSemver] = useState("1.5.0");
  const [file, setFile] = useState<File | null>(null);
  const [locator, setLocator] = useState("");
  const [digest, setDigest] = useState<FirmwareHash | null>(null);
  const [hashing, setHashing] = useState(false);

  async function chooseFile(selected: File | null) {
    setFile(selected);
    setDigest(null);
    if (!selected) return;

    setLocator(`${firmwareBaseUrl.replace(/\/*$/, "/")}${selected.name}`);
    setHashing(true);
    try {
      setDigest(await hasher.hash(selected));
    } finally {
      setHashing(false);
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    await onPublish({ semver, file, locator });
  }

  return (
    <section className="panel">
      <h2>Publish a release</h2>
      <p className="hint">
        The file is hashed in this browser and never uploaded. Only the 32-byte
        fingerprint goes on-chain.
      </p>

      <form onSubmit={submit}>
        <div className="row">
          <div className="field">
            <label htmlFor="model">Device model</label>
            <input id="model" type="text" value={model} readOnly />
          </div>
          <div className="field">
            <label htmlFor="semver">Version</label>
            <input
              id="semver"
              type="text"
              value={semver}
              placeholder="1.5.0"
              onChange={(event) => setSemver(event.target.value)}
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="firmware">Firmware image</label>
          <input
            id="firmware"
            type="file"
            onChange={(event) => void chooseFile(event.target.files?.[0] ?? null)}
          />
        </div>

        {hashing && <p className="hint">computing SHA-256…</p>}

        {digest && (
          <div className="digest">
            <div className="label">SHA-256 — computed locally</div>
            <div className="value mono">{digest.hex}</div>
          </div>
        )}

        <div className="field">
          <label htmlFor="locator">Locator</label>
          <input
            id="locator"
            type="text"
            value={locator}
            placeholder="http://127.0.0.1:8081/firmware/…"
            onChange={(event) => setLocator(event.target.value)}
          />
        </div>

        <button type="submit" disabled={busy || hashing || !file}>
          {busy ? "Publishing…" : "Publish to the ledger"}
        </button>
      </form>
    </section>
  );
}
