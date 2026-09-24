import { expect } from "chai";
import { ethers } from "hardhat";
import { loadFixture } from "@nomicfoundation/hardhat-network-helpers";

const MODEL = "RUH-SENSOR-01";
const OTHER_MODEL = "RUH-GATEWAY-99";

const V1_2_0 = 10200;
const V1_3_0 = 10300;
const V1_4_0 = 10400;

const hashOf = (text: string) => ethers.keccak256(ethers.toUtf8Bytes(text));
const HASH_A = hashOf("firmware-1.2.0");
const HASH_B = hashOf("firmware-1.3.0");
const HASH_C = hashOf("firmware-1.4.0");

const LOCATOR = "http://127.0.0.1:8081/firmware/RUH-SENSOR-01-1.4.0.bin";

async function deployed() {
  const [admin, manufacturer, outsider] = await ethers.getSigners();
  const registry = await ethers.deployContract("FirmwareRegistry", [
    admin.address,
  ]);
  await registry.waitForDeployment();

  const MANUFACTURER_ROLE = await registry.MANUFACTURER_ROLE();
  await registry.grantRole(MANUFACTURER_ROLE, manufacturer.address);

  return { registry, admin, manufacturer, outsider, MANUFACTURER_ROLE };
}

describe("FirmwareRegistry", () => {
  describe("deployment and roles", () => {
    it("grants the deployer both admin and manufacturer roles", async () => {
      const { registry, admin, MANUFACTURER_ROLE } = await loadFixture(deployed);
      const DEFAULT_ADMIN_ROLE = await registry.DEFAULT_ADMIN_ROLE();

      expect(await registry.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to.equal(
        true
      );
      expect(await registry.hasRole(MANUFACTURER_ROLE, admin.address)).to.equal(
        true
      );
    });

    it("reports nothing published for an unknown model", async () => {
      const { registry } = await loadFixture(deployed);

      // Zero rather than a revert: a device asks "is there anything for me?"
      // with one cheap call and no revert handling.
      expect(await registry.latestVersion("NEVER-SEEN")).to.equal(0);
      expect(await registry.releaseCount("NEVER-SEEN")).to.equal(0);
    });
  });

  describe("publishRelease — access control", () => {
    it("rejects a publisher without the manufacturer role", async () => {
      const { registry, outsider } = await loadFixture(deployed);

      await expect(
        registry
          .connect(outsider)
          .publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR)
      ).to.be.revertedWithCustomError(
        registry,
        "AccessControlUnauthorizedAccount"
      );
    });

    it("accepts a publisher holding the manufacturer role", async () => {
      const { registry, manufacturer } = await loadFixture(deployed);

      await expect(
        registry
          .connect(manufacturer)
          .publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR)
      ).to.emit(registry, "ReleasePublished");
    });

    it("lets the admin revoke the manufacturer role", async () => {
      const { registry, manufacturer, MANUFACTURER_ROLE } = await loadFixture(
        deployed
      );
      await registry.revokeRole(MANUFACTURER_ROLE, manufacturer.address);

      await expect(
        registry
          .connect(manufacturer)
          .publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR)
      ).to.be.revertedWithCustomError(
        registry,
        "AccessControlUnauthorizedAccount"
      );
    });
  });

  describe("publishRelease — validation", () => {
    it("stores the release and updates the latest pointer", async () => {
      const { registry } = await loadFixture(deployed);

      // `model` is indexed, so on-chain it is stored as keccak256 of the string.
      // The matcher expects the pre-image and hashes it for comparison.
      await expect(registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR))
        .to.emit(registry, "ReleasePublished")
        .withArgs(MODEL, V1_4_0, HASH_C, LOCATOR);

      expect(await registry.latestVersion(MODEL)).to.equal(V1_4_0);
      expect(await registry.releaseCount(MODEL)).to.equal(1);

      const release = await registry.latestRelease(MODEL);
      expect(release.version).to.equal(V1_4_0);
      expect(release.firmwareHash).to.equal(HASH_C);
      expect(release.locator).to.equal(LOCATOR);
      expect(release.revoked).to.equal(false);
      expect(release.publishedAt).to.be.greaterThan(0);
    });

    it("rejects a zero firmware hash", async () => {
      const { registry } = await loadFixture(deployed);

      await expect(
        registry.publishRelease(MODEL, V1_4_0, ethers.ZeroHash, LOCATOR)
      ).to.be.revertedWithCustomError(registry, "EmptyFirmwareHash");
    });

    it("rejects an empty locator", async () => {
      const { registry } = await loadFixture(deployed);

      await expect(
        registry.publishRelease(MODEL, V1_4_0, HASH_C, "")
      ).to.be.revertedWith("FirmwareRegistry: empty locator");
    });
  });

  describe("rollback prevention", () => {
    it("rejects republishing the same version", async () => {
      const { registry } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR);

      await expect(registry.publishRelease(MODEL, V1_4_0, HASH_B, LOCATOR))
        .to.be.revertedWithCustomError(registry, "NonMonotonicVersion")
        .withArgs(V1_4_0, V1_4_0);
    });

    it("rejects publishing an older version after a newer one", async () => {
      const { registry } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR);

      // The attack a signature check cannot see: the old image is genuine and
      // correctly signed, but its vulnerability is public. Ordering catches it.
      await expect(registry.publishRelease(MODEL, V1_2_0, HASH_A, LOCATOR))
        .to.be.revertedWithCustomError(registry, "NonMonotonicVersion")
        .withArgs(V1_2_0, V1_4_0);
    });

    it("accepts strictly increasing versions", async () => {
      const { registry } = await loadFixture(deployed);

      await registry.publishRelease(MODEL, V1_2_0, HASH_A, LOCATOR);
      await registry.publishRelease(MODEL, V1_3_0, HASH_B, LOCATOR);
      await registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR);

      expect(await registry.latestVersion(MODEL)).to.equal(V1_4_0);
      expect(await registry.releaseCount(MODEL)).to.equal(3);
    });

    it("keeps history readable after newer releases land", async () => {
      const { registry } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_2_0, HASH_A, LOCATOR);
      await registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR);

      const old = await registry.releaseAt(MODEL, V1_2_0);
      expect(old.firmwareHash).to.equal(HASH_A);
      expect(await registry.versionAt(MODEL, 0)).to.equal(V1_2_0);
      expect(await registry.versionAt(MODEL, 1)).to.equal(V1_4_0);
    });
  });

  describe("revocation", () => {
    it("flags a release and emits", async () => {
      const { registry } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_3_0, HASH_B, LOCATOR);

      await expect(registry.revokeRelease(MODEL, V1_3_0))
        .to.emit(registry, "ReleaseRevoked")
        .withArgs(MODEL, V1_3_0);

      const release = await registry.releaseAt(MODEL, V1_3_0);
      expect(release.revoked).to.equal(true);
    });

    it("rejects revoking an unknown release", async () => {
      const { registry } = await loadFixture(deployed);

      await expect(registry.revokeRelease(MODEL, V1_3_0))
        .to.be.revertedWithCustomError(registry, "UnknownRelease")
        .withArgs(MODEL, V1_3_0);
    });

    it("is one-way — revoking twice reverts", async () => {
      const { registry } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_3_0, HASH_B, LOCATOR);
      await registry.revokeRelease(MODEL, V1_3_0);

      await expect(registry.revokeRelease(MODEL, V1_3_0))
        .to.be.revertedWithCustomError(registry, "AlreadyRevoked")
        .withArgs(MODEL, V1_3_0);
    });

    it("rejects revocation by a non-manufacturer", async () => {
      const { registry, outsider } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_3_0, HASH_B, LOCATOR);

      await expect(
        registry.connect(outsider).revokeRelease(MODEL, V1_3_0)
      ).to.be.revertedWithCustomError(
        registry,
        "AccessControlUnauthorizedAccount"
      );
    });

    it("does not block publishing a newer fixed release", async () => {
      const { registry } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_3_0, HASH_B, LOCATOR);
      await registry.revokeRelease(MODEL, V1_3_0);

      // Withdrawing a vulnerable release must not wedge the update channel.
      await registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR);
      expect(await registry.latestVersion(MODEL)).to.equal(V1_4_0);
    });
  });

  describe("reads on absent data", () => {
    it("reverts latestRelease when nothing is published", async () => {
      const { registry } = await loadFixture(deployed);

      await expect(registry.latestRelease(MODEL))
        .to.be.revertedWithCustomError(registry, "UnknownRelease")
        .withArgs(MODEL, 0);
    });

    it("reverts releaseAt for a version that was never published", async () => {
      const { registry } = await loadFixture(deployed);
      await registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR);

      await expect(registry.releaseAt(MODEL, V1_2_0))
        .to.be.revertedWithCustomError(registry, "UnknownRelease")
        .withArgs(MODEL, V1_2_0);
    });
  });

  describe("model isolation", () => {
    it("keeps each model in its own namespace", async () => {
      const { registry } = await loadFixture(deployed);

      await registry.publishRelease(MODEL, V1_4_0, HASH_C, LOCATOR);
      await registry.publishRelease(OTHER_MODEL, V1_2_0, HASH_A, LOCATOR);

      // A high version on one model must not block a low version on another,
      // or one product line's release cadence would gate every other.
      expect(await registry.latestVersion(MODEL)).to.equal(V1_4_0);
      expect(await registry.latestVersion(OTHER_MODEL)).to.equal(V1_2_0);
      expect(await registry.releaseCount(MODEL)).to.equal(1);
      expect(await registry.releaseCount(OTHER_MODEL)).to.equal(1);
    });
  });
});
