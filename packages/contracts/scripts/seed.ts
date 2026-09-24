import { createHash } from "crypto";
import * as fs from "fs";
import * as path from "path";
import hre, { ethers } from "hardhat";

/**
 * Publish the three shared fixture releases onto a deployed registry.
 *
 * Digests are derived from the same `payload` field the device client hashes, so
 * the chain and the fixture cannot disagree. Nothing is typed in by hand.
 *
 * Set FIRMWARE_BASE_URL to point the locators at Member 4's firmware server;
 * it defaults to the local one used during rehearsal.
 */

const FIXTURE_PATH = path.join(
  __dirname,
  "..",
  "..",
  "shared",
  "fixtures",
  "sample-releases.json"
);

const BASE_URL = (
  process.env.FIRMWARE_BASE_URL ?? "http://127.0.0.1:8081/"
).replace(/\/*$/, "/");

type Fixture = {
  deviceModel: string;
  releases: {
    version: number;
    semver: string;
    payload: string;
    locator: string;
    revoked?: boolean;
  }[];
};

async function main() {
  const network = hre.network.name;
  const deploymentPath = path.join(
    __dirname,
    "..",
    "deployments",
    `${network}.json`
  );

  if (!fs.existsSync(deploymentPath)) {
    throw new Error(
      `No deployment found for ${network}. Run \`npm run deploy:${
        network === "sepolia" ? "sepolia" : "local"
      }\` first.`
    );
  }

  const { address } = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
  const fixture: Fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8"));
  const registry = await ethers.getContractAt("FirmwareRegistry", address);

  console.log(`registry  ${address}`);
  console.log(`model     ${fixture.deviceModel}`);
  console.log(`base url  ${BASE_URL}\n`);

  // Ascending order is mandatory: the contract enforces strict monotonicity, so
  // seeding out of order reverts rather than silently producing odd state.
  const ordered = [...fixture.releases].sort((a, b) => a.version - b.version);

  for (const release of ordered) {
    const digest =
      "0x" + createHash("sha256").update(release.payload, "utf8").digest("hex");
    const locator = BASE_URL + release.locator.replace(/^\/+/, "");

    const existing = await registry.latestVersion(fixture.deviceModel);
    if (existing >= BigInt(release.version)) {
      console.log(`  v${release.semver}  already published, skipping`);
      continue;
    }

    const tx = await registry.publishRelease(
      fixture.deviceModel,
      release.version,
      digest,
      locator
    );
    await tx.wait();
    console.log(`  v${release.semver}  published   ${digest}`);
  }

  // Revoke afterwards, so the revoked release still occupies its place in the
  // version history — exactly the situation a real fleet is in after a CVE.
  for (const release of ordered.filter((entry) => entry.revoked)) {
    const current = await registry.releaseAt(
      fixture.deviceModel,
      release.version
    );
    if (current.revoked) {
      console.log(`  v${release.semver}  already revoked, skipping`);
      continue;
    }
    const tx = await registry.revokeRelease(
      fixture.deviceModel,
      release.version
    );
    await tx.wait();
    console.log(`  v${release.semver}  REVOKED`);
  }

  const latest = await registry.latestRelease(fixture.deviceModel);
  console.log(
    `\nlatest is v${Number(latest.version)} -> ${latest.firmwareHash}`
  );
  console.log(`count: ${await registry.releaseCount(fixture.deviceModel)}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
