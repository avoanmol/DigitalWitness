import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import { network } from "hardhat";

const networkName = process.env.DW_NETWORK ?? "hardhatMainnet";
const { viem } = await network.create({ network: networkName });

const contract = await viem.deployContract("EvidenceAnchor");
const publicClient = await viem.getPublicClient();
const chainId = await publicClient.getChainId();

const deployment = {
  network: networkName,
  chainId,
  address: contract.address,
};

const outputDirectory = resolve("contracts", "deployments");
const outputPath = resolve(outputDirectory, `${networkName}.json`);

await mkdir(outputDirectory, { recursive: true });
await writeFile(outputPath, `${JSON.stringify(deployment, null, 2)}\n`);

console.log(`EvidenceAnchor deployed at ${contract.address}`);
console.log(`CHAIN_CONTRACT_ADDRESS=${contract.address}`);
console.log(`Saved ${outputPath}`);