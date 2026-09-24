/**
 * Domain layer — plain TypeScript, no React and no ethers.
 *
 * The dependency rule for this package mirrors the device client's: nothing here
 * may import from `application`, `infrastructure`, `composition` or `ui`, and no
 * UI component may import ethers directly. `npm run check:layering` enforces it.
 */

export { FirmwareHash, InvalidFirmwareHash } from "./FirmwareHash";
export { FirmwareVersion, InvalidFirmwareVersion } from "./FirmwareVersion";
export { byNewestFirst, isInstallable } from "./Release";
export type { DraftRelease, Release } from "./Release";
