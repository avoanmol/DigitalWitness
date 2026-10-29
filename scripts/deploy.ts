import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import type {} from "@nomicfoundation/hardhat-viem";
import { artifacts, network } from "hardhat";

const networkName = process.env.DW_NETWORK ?? "hardhatMainnet";
const { viem } = await network.create({ network: networkName });
const publicClient = await viem.getPublicClient();
const chainId = await publicClient.getChainId();
if (networkName === "amoy" && chainId !== 80002) throw new Error("Amoy RPC returned the wrong chain ID");
const { contract, deploymentTransaction } = await viem.sendDeploymentTransaction("EvidenceAnchor");
const receipt = await publicClient.waitForTransactionReceipt({
  hash: deploymentTransaction.hash, confirmations: chainId === 31337 ? 1 : 2,
});
if (receipt.status !== "success") throw new Error("Contract deployment reverted");
const artifact = await artifacts.readArtifact("EvidenceAnchor");
const deployment = {
  network: networkName, chainId, address: contract.address,
  transactionHash: receipt.transactionHash, blockNumber: Number(receipt.blockNumber),
  owner: await contract.read.owner(), abi: artifact.abi,
  deployedAt: new Date().toISOString(),
};
const outputDirectory = resolve("contracts", "deployments");
const outputPath = resolve(outputDirectory, `${networkName}.json`);
await mkdir(outputDirectory, { recursive: true });
await writeFile(outputPath, `${JSON.stringify(deployment, null, 2)}\n`);
console.log(`EvidenceAnchor deployed at ${contract.address}`);
console.log(`CHAIN_CONTRACT_ADDRESS=${contract.address}`);
console.log(`Transaction: ${receipt.transactionHash}`);
console.log(`Saved ${outputPath}`);
