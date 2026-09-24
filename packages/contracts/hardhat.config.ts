import type { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

// Secrets come from the environment, never from source control. `.env` is
// gitignored; see .env.example for the variables a testnet deploy needs.
const SEPOLIA_RPC_URL = process.env.SEPOLIA_RPC_URL ?? "";
const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY ?? "";
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY ?? "";

// Overridable so the same `--network localhost` commands work from inside a
// container, where the node is a sibling service rather than 127.0.0.1.
const LOCALHOST_RPC_URL =
  process.env.LOCALHOST_RPC_URL ?? "http://127.0.0.1:8545";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      // The registry is written once per release and read by every device on
      // every check, so optimising for many runs is the right trade.
      optimizer: { enabled: true, runs: 1000 },
    },
  },
  networks: {
    hardhat: {},
    localhost: { url: LOCALHOST_RPC_URL },
    ...(SEPOLIA_RPC_URL && DEPLOYER_PRIVATE_KEY
      ? {
          sepolia: {
            url: SEPOLIA_RPC_URL,
            accounts: [DEPLOYER_PRIVATE_KEY],
          },
        }
      : {}),
  },
  etherscan: { apiKey: ETHERSCAN_API_KEY },
  gasReporter: { enabled: process.env.REPORT_GAS === "true" },
};

export default config;
