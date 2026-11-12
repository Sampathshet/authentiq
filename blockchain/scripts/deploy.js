const fs = require("node:fs");
const path = require("node:path");
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const factory = await hre.ethers.getContractFactory("AuthentiqRegistry");
  const registry = await factory.deploy();
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const network = await hre.ethers.provider.getNetwork();
  const payload = {
    contract: "AuthentiqRegistry",
    address,
    chainId: Number(network.chainId),
    deployer: deployer.address,
    deployedAt: new Date().toISOString()
  };

  const destination = path.join(__dirname, "..", "deployments", `${network.chainId}.json`);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.writeFileSync(destination, JSON.stringify(payload, null, 2));

  console.log(JSON.stringify(payload, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
