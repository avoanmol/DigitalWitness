# DigitalWitness

DigitalWitness is a team project for preserving digital evidence and checking whether a file has changed since it was recorded. The design uses SHA-256 hashes and a Merkle tree off-chain, with only a batch root and its leaf count written to the blockchain.

> **Project status:** The integrity and local blockchain feature is implemented on `feat/a-merkle-contract`. It has unit tests and local Hardhat support. The shared API, database migrations, object storage, audit logging, and worker integration are still team integration work. The integrity database and API documents in `docs/` are proposals, not implemented endpoints or migrations.

## What is in this repository

- `backend/app/integrity/` - Merkle tree, chain RPC, batch construction, and verification services.
- `backend/tests/` - Python unit tests for the integrity services.
- `contracts/EvidenceAnchor.sol` - contract that records a Merkle root and leaf count.
- `test/EvidenceAnchor.ts` - contract tests.
- `scripts/deploy.ts` - deploys the contract and writes a local deployment record under `contracts/deployments/`.
- `docs/merkle-spec.md` - hash, ordering, proof, and verification rules.
- `docs/integrity-db-contract.md` and `docs/integrity-api-contract.md` - proposed integration contracts for the team.

## Requirements

- Node.js 24 or newer and npm.
- Python 3.11 for the backend integrity code and Python tests.
- Windows PowerShell commands are shown below. On Windows, use the `.cmd` Hardhat executable if PowerShell blocks `npx.ps1` due to execution policy.

## Get the project

```powershell
git clone https://github.com/avoanmol/DigitalWitness.git
Set-Location DigitalWitness
```

To use the current integrity feature before it is merged, check out its branch:

```powershell
git switch feat/a-merkle-contract
```

## Install dependencies

Install the Node dependencies:

```powershell
npm install
```

Create a Python virtual environment and install the backend requirements:

```powershell
py -3.11 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

If `py -3.11` is unavailable, use the full path to your Python 3.11 executable in both commands.

## Run the tests

Run the Solidity and TypeScript tests:

```powershell
.\node_modules\.bin\hardhat.cmd test
```

Run the Python integrity tests:

```powershell
& .\backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

## Run a local blockchain demo

Open a first PowerShell window in the repository and start a local Hardhat node:

```powershell
.\node_modules\.bin\hardhat.cmd node
```

Leave that window open. In a second PowerShell window, deploy the contract to that node:

```powershell
$env:DW_NETWORK = "localhost"
try {
    .\node_modules\.bin\hardhat.cmd run scripts\deploy.ts
}
finally {
    Remove-Item Env:DW_NETWORK -ErrorAction SilentlyContinue
}
```

The deploy command prints `CHAIN_CONTRACT_ADDRESS` and saves the deployment details to `contracts/deployments/localhost.json`. The deployment file is local output; do not commit it.

The Python chain service defaults to `http://127.0.0.1:8545`. Before calling it, set the deployed address and an unlocked account from the **local Hardhat node**:

```powershell
$env:CHAIN_RPC_URL = "http://127.0.0.1:8545"
$env:CHAIN_CONTRACT_ADDRESS = "<address printed by deploy>"
$env:CHAIN_SENDER_ADDRESS = "<unlocked account printed by the local Hardhat node>"
```

Keep the local node running while using the chain service. These example accounts are for local development only. Never use Hardhat's published test keys on a public network.

## Polygon Amoy configuration

The Hardhat `amoy` network uses chain ID `80002`. Set the RPC URL and a funded Amoy test account's private key in the local environment before deploying:

```powershell
$env:AMOY_RPC_URL = "<Amoy RPC URL>"
$env:AMOY_PRIVATE_KEY = "<Amoy test account private key>"
.\node_modules\.bin\hardhat.cmd run scripts\deploy.ts --network amoy
```

For Python chain submissions, configure `CHAIN_RPC_URL`, `CHAIN_CONTRACT_ADDRESS`, and `CHAIN_PRIVATE_KEY`. Keep these values out of source control and use test funds only. The project uses two confirmations for Amoy and one for the local Hardhat chain.

## Integrity rules

- A file's SHA-256 digest is calculated from the original bytes.
- Evidence is ordered by upload time, then evidence ID.
- Leaf hashes use `SHA-256(0x00 || file_hash)`; parent hashes use `SHA-256(0x01 || left || right)`.
- An unpaired node is promoted unchanged to the next tree level.
- Only the Merkle root and leaf count are recorded on-chain. File contents, names, and individual evidence hashes do not belong on-chain.
- A valid proof shows that the supplied hash is part of the anchored batch. It does not prove the evidence was authentic before it was uploaded.
- Verification outcomes are `verified`, `altered`, `pending`, or `error`. A storage or blockchain outage is an error, not evidence of alteration.

See [the Merkle specification](docs/merkle-spec.md) for the full rules and [the proposed integration contracts](docs/integrity-api-contract.md) for API and database assumptions.

## Team integration boundary

The integrity services currently operate on supplied records and chain configuration. They are not yet connected to the shared application's API, database, evidence storage, or background worker. Member B owns the shared schema and migrations; coordinate the final table names and fields with them before wiring persistence. Confirm the API shapes with the teammate who owns the API before implementing the routes.

Do not create a separate migration history for integrity tables. Add agreed tables to the application's existing migration system when the backend owner provides it.

## Security

- Never commit `.env` files, private keys, RPC credentials, or local deployment output.
- Do not put evidence content, personal information, or individual file hashes on-chain.
- Use local Hardhat accounts only against the local development chain.
