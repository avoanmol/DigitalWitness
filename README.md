# DigitalWitness

DigitalWitness preserves digital evidence and checks whether it has changed since upload. It hashes evidence with SHA-256, builds Merkle trees off-chain, and anchors only each batch root and leaf count on-chain.

## Status

Member A's integrity services, `EvidenceAnchor` contract, local Hardhat setup, and focused tests are on `feat/a-merkle-contract`. API routes, database persistence and migrations, object storage, audit logging, and worker integration depend on the shared backend and finalized schema. The API and database documents in `docs/` are proposals, not migrations or live endpoints.

## Integrity rules

- Order evidence by `uploaded_at`, then `evidence_id`.
- Hash leaves with `SHA-256(0x00 || file_hash)` and parents with `SHA-256(0x01 || left || right)`; promote an unpaired node unchanged.
- Anchor batches at 10 items or when the oldest item reaches 30 seconds. Retry delays are 5, 15, and 45 seconds.
- Store only the Merkle root and leaf count on-chain. Never put evidence content, personal information, or individual file hashes on-chain.
- Verification results are `verified`, `altered`, `pending`, or `error`. Storage or RPC failure is `error`, not `altered`.

See [the Merkle specification](docs/merkle-spec.md) and the proposed [database](docs/integrity-db-contract.md) and [API](docs/integrity-api-contract.md) contracts.

## Local development

Requirements: Node.js 24+, npm, and Python 3.11.

```powershell
git clone https://github.com/avoanmol/DigitalWitness.git
Set-Location DigitalWitness
git switch feat/a-merkle-contract
npm install
py -3.11 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Run the tests:

```powershell
.\node_modules\.bin\hardhat.cmd test
& .\backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

For a local chain, start `.\node_modules\.bin\hardhat.cmd node` in one terminal. In another, deploy with:

```powershell
$env:DW_NETWORK = "localhost"
.\node_modules\.bin\hardhat.cmd run scripts\deploy.ts
Remove-Item Env:DW_NETWORK
```

The deploy script prints the contract address and writes local output under `contracts/deployments/`. The Python chain client uses `CHAIN_RPC_URL` (default `http://127.0.0.1:8545`), `CHAIN_CONTRACT_ADDRESS`, and a local unlocked `CHAIN_SENDER_ADDRESS`. Do not use Hardhat development keys on public networks or commit credentials/deployment output.

## Team boundary

Member B owns the shared schema and migration history. Agree on the final schema before wiring persistence; add integrity tables to the existing migrations. Coordinate API shapes with the teammate responsible for the API. Do not create a separate migration history.
