// Disposable local development chain. Never use these public accounts on a live network.
import { spawn } from "node:child_process";
import { readFile, writeFile, mkdir } from "node:fs/promises";
const cli = "node_modules/hardhat/dist/src/cli.js";
const child = spawn(process.execPath, [cli, "node", "--hostname", "0.0.0.0"], { stdio: "inherit" });
let stopping = false;
for (const signal of ["SIGTERM", "SIGINT"]) process.on(signal, () => { stopping = true; child.kill(signal); });
child.on("exit", code => process.exit(stopping ? 0 : (code || 1)));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function rpc(method, params = []) {
  const response = await fetch("http://127.0.0.1:8545", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    signal: AbortSignal.timeout(3000),
  });
  const result = await response.json();
  if (result.error) throw new Error("Local RPC rejected " + method);
  return result.result;
}
try {
  let ready = false;
  for (let attempt = 0; attempt < 120; attempt++) {
    try { ready = await rpc("eth_chainId") === "0x7a69"; } catch {}
    if (ready) break;
    await sleep(500);
  }
  if (!ready) throw new Error("Local chain did not start");
  const artifact = JSON.parse(await readFile("artifacts/contracts/EvidenceAnchor.sol/EvidenceAnchor.json", "utf8"));
  const [owner] = await rpc("eth_accounts");
  const transactionHash = await rpc("eth_sendTransaction", [{ from: owner, data: artifact.bytecode }]);
  let receipt;
  for (let attempt = 0; attempt < 120; attempt++) {
    receipt = await rpc("eth_getTransactionReceipt", [transactionHash]);
    if (receipt) break;
    await sleep(500);
  }
  if (receipt?.status !== "0x1") throw new Error("Local deployment failed");
  const deployment = { network: "docker-local", chainId: 31337, address: receipt.contractAddress,
    owner, transactionHash, blockNumber: Number(BigInt(receipt.blockNumber)), abi: artifact.abi };
  await mkdir("contracts/deployments", { recursive: true });
  await writeFile("contracts/deployments/docker-local.json", JSON.stringify(deployment, null, 2));
  console.log("Local EvidenceAnchor ready at " + deployment.address);
} catch (error) { console.error(error.message); child.kill(); process.exitCode = 1; }
