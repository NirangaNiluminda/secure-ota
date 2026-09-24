import * as fs from "fs";
import * as path from "path";
import hre, { ethers } from "hardhat";

/**
 * Deploy FirmwareRegistry and record the address where the other packages can
 * find it.
 *
 * The device client and the dashboard both read deployments/<network>.json, so
 * nobody hard-codes an address and nobody has to paste one into a group chat.
 */

const SPEC_PATH = path.join(
  __dirname,
  "..",
  "..",
  "shared",
  "abi",
  "FirmwareRegistry.json"
);

async function main() {
  const [deployer] = await ethers.getSigners();
  const network = hre.network.name;
  const balance = await ethers.provider.getBalance(deployer.address);

  console.log(`network   ${network}`);
  console.log(`deployer  ${deployer.address}`);
  console.log(`balance   ${ethers.formatEther(balance)} ETH\n`);

  if (balance === 0n) {
    throw new Error(
      `${deployer.address} has no balance on ${network}. Fund it from a faucet ` +
        `before deploying — do this on integration day, not the night before.`
    );
  }

  const registry = await ethers.deployContract("FirmwareRegistry", [
    deployer.address,
  ]);
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const receipt = await registry.deploymentTransaction()?.wait();
  const spec = JSON.parse(fs.readFileSync(SPEC_PATH, "utf8"));

  const record = {
    network,
    chainId: Number((await ethers.provider.getNetwork()).chainId),
    address,
    deployer: deployer.address,
    blockNumber: receipt?.blockNumber ?? null,
    abiSpecVersion: spec.specVersion,
    deployedAt: new Date().toISOString(),
  };

  const outputDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(
    path.join(outputDir, `${network}.json`),
    JSON.stringify(record, null, 2) + "\n"
  );

  console.log(`FirmwareRegistry deployed to ${address}`);
  console.log(`recorded in deployments/${network}.json\n`);
  console.log("Next:");
  console.log(`  npm run seed:${network === "sepolia" ? "sepolia" : "local"}`);
  console.log(
    `  device: python3 -m secure_ota_device.cli.main --contract ${address} status`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
