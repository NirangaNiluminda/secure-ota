import type { Release } from "../../domain";

interface Props {
  releases: Release[];
  latestInstallable: Release | null;
  busy: boolean;
  onRevoke: (release: Release) => void;
}

/**
 * The release history.
 *
 * "Devices accept" marks the newest release that has not been withdrawn — the
 * one a device would actually install right now. It makes the effect of a
 * revocation visible the instant the transaction confirms, which is the whole
 * point of the revocation beat in the demo.
 */
export function ReleaseTable({
  releases,
  latestInstallable,
  busy,
  onRevoke,
}: Props) {
  if (releases.length === 0) {
    return (
      <section className="panel">
        <h2>Releases</h2>
        <p className="hint">Nothing published for this model yet.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>Releases</h2>
      <p className="hint">
        Newest first. Revocation is permanent — a withdrawn release can never be
        reinstated, only superseded.
      </p>

      <table>
        <thead>
          <tr>
            <th>Version</th>
            <th>SHA-256</th>
            <th>Published</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {releases.map((release) => {
            const accepted =
              latestInstallable?.version.code === release.version.code;
            return (
              <tr
                key={release.version.code}
                className={release.revoked ? "revoked" : ""}
              >
                <td className="version mono">{release.version.toString()}</td>
                <td className="mono">{release.firmwareHash.short}</td>
                <td>{release.publishedAt.toISOString().slice(0, 10)}</td>
                <td>
                  {release.revoked ? (
                    <span className="badge revoked">revoked</span>
                  ) : accepted ? (
                    <span className="badge live">devices accept</span>
                  ) : (
                    <span className="badge">superseded</span>
                  )}
                </td>
                <td>
                  {!release.revoked && (
                    <button
                      className="danger"
                      disabled={busy}
                      onClick={() => onRevoke(release)}
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
