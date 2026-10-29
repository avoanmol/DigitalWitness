import { readFile } from "node:fs/promises";
try {
  const deployment = JSON.parse(await readFile("contracts/deployments/docker-local.json", "utf8"));
  const response = await fetch("http://127.0.0.1:8545", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({jsonrpc:"2.0", id:1, method:"eth_getCode", params:[deployment.address,"latest"]}), signal: AbortSignal.timeout(2000) });
  const data = await response.json();
  process.exit(data.result && data.result !== "0x" ? 0 : 1);
} catch { process.exit(1); }
