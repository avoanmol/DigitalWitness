# DigitalWitness

**Case-based evidence preservation and investigation, with tamper-evident proof on Polygon Amoy.**

DigitalWitness is a demo that fingerprints every upload with SHA-256, encrypts the original file in object storage, issues a signed receipt, and anchors batches of fingerprints on-chain. It also surfaces OCR, entity matching, and harassment-category suggestions as leads for human reviewers.

> [!IMPORTANT]
> **Leads, not verdicts.** OCR, entity matching, category suggestions, and optional model output are investigative leads for human review. They do not determine truth, guilt, or whether media is authentic. This project has no validated deepfake detector and makes no real-world accuracy claims.
>
> **Use synthetic or consented, de-identified evidence only.**

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Evidence and investigation](#evidence-and-investigation)
- [Blockchain anchoring](#blockchain-anchoring)
- [AI analysis and limitations](#ai-analysis-and-limitations)
- [Testing](#testing)
- [Operations](#operations)
- [Documentation](#documentation)

## Features

- **Integrity:** SHA-256 fingerprint of the original bytes, with an HMAC-signed receipt recording the fingerprint and custody identifiers.
- **Confidentiality:** evidence is encrypted with AES-256-GCM and stored outside the database.
- **Anchoring:** batches of fingerprints are committed as a Merkle root on Polygon Amoy (chain ID 80002).
- **Investigation:** OCR/extraction coverage, five configurable harassment focus categories, entities, suggested case links, and threat flags, all requiring human decisions.
- **Accountability:** append-only audit chain that admin and legal roles can inspect and verify.
- **Role-based access:** reporter, investigator, legal, and admin roles.

## Architecture

`docker compose` starts six services:

| Service | Purpose |
| --- | --- |
| PostgreSQL | Cases, receipts, audit chain, accounts |
| Silo-compatible object storage | Encrypted evidence files |
| FastAPI | Backend API |
| Next.js | Website |
| Integrity worker | Batching, Merkle roots, on-chain anchoring |
| AI analysis worker | OCR, entity matching, category suggestions |

## Quick start

### Prerequisites

- Docker Desktop and Git
- Node.js 20.9+ and Python 3.11 (only needed to run tests)

### 1. Configure

```powershell
Copy-Item .env.example .env
```

Replace the local secret placeholders in `.env`, or run `scripts/setup_local_env.py` to generate them (it only runs if `.env` does not exist).

Then set the chain values for the Polygon Amoy deployment and wallet you intend to demo:

```env
CHAIN_EXPECTED_ID=80002
CHAIN_RPC_URL=<your Amoy RPC URL>
CHAIN_CONTRACT_ADDRESS=<EvidenceAnchor address>
CHAIN_SENDER_ADDRESS=<signing wallet address>
```

Put the wallet signing key in `.env` only.

> [!WARNING]
> Never commit `.env`, and never use a funded wallet's key in a public repository. Use a test wallet.

To use the live API instead of mock data, set `NEXT_PUBLIC_USE_MOCK=false`. Leave `LLM_ENABLED=false` unless your chosen provider is approved for the evidence you submit.

### 2. Start the services

```powershell
docker compose up --build -d
docker compose ps
```

| Interface | URL |
| --- | --- |
| Website | http://localhost:3000 |
| API reference | http://127.0.0.1:8000/docs |

The website is built with mock mode **on** by default. After changing `NEXT_PUBLIC_USE_MOCK` in `.env`, rebuild the web service.

### 3. Create the first administrator

New registrations are reporters. Create the first admin from the API container:

```powershell
docker compose exec -it api python -m backend.bootstrap_admin admin@example.test --name "Workspace Admin"
```

Then assign investigator and legal roles from the admin page.

## Configuration

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_USE_MOCK` | `true` (build default) uses mock data; `false` uses the live API. Requires a web rebuild. |
| `LLM_ENABLED` | Enables optional model analysis. Keep `false` unless the provider is approved for your evidence. |
| `CHAIN_EXPECTED_ID` | Defaults to `80002` (Polygon Amoy). The worker refuses to broadcast if the RPC reports a different chain. |
| `CHAIN_RPC_URL` | RPC endpoint for the target chain. |
| `CHAIN_CONTRACT_ADDRESS` | `EvidenceAnchor` deployment on that same RPC. |
| `CHAIN_SENDER_ADDRESS` | Must match the signing wallet, which needs test POL for gas. |

See `.env.example` for the full list.

## Evidence and investigation

**Accepted files:** JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV, WEBM, up to 100 MB each.

On upload, the API:

1. Checks the file signature against the supported types.
2. Hashes the original bytes (SHA-256).
3. Encrypts the file (AES-256-GCM) and stores it outside the database.
4. Issues a canonical HMAC-signed receipt with the fingerprint and custody identifiers.

Investigators review the analysis output and make the final call on every link and flag.

## Blockchain anchoring

The demo uses **Polygon Amoy (chain ID 80002)**. Only each Merkle root and its leaf count are written on-chain. Evidence, personal details, and individual file hashes stay off-chain.

**Merkle tree rules**

- Leaf: `SHA-256(0x00 || file_hash)`
- Parent: `SHA-256(0x01 || left || right)`
- An unpaired node is promoted unchanged.

**Notes**

- If storage or the RPC is unavailable, verification returns `error`. It is never labeled `altered`.
- A local Hardhat chain is available only through the explicit `compose.local-chain.yml` development profile, which overrides the expected ID to `31337`. It is disposable, and its transactions are not Amoy transactions.
- Do not point an existing database that has confirmed batches at a freshly reset local chain.

## AI analysis and limitations

- Video analysis samples at most four frames, from videos up to 60 seconds.
- Audio is preserved but **not transcribed**.
- Metadata, OCR, sparse frames, and optional model output cannot prove that a screenshot or video is real or fake.
- All suggestions require human review.

See the AI behavior and limitations document and the evaluation protocol for details.

## Testing

Run these from the repository root in PowerShell:

```powershell
# Smart contract tests
.\node_modules\.bin\hardhat.cmd test

# Backend and project tests
& .\backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
& .\backend\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v

# Frontend
Set-Location frontend
npm run lint
npm run typecheck
npm run build
Set-Location ..
```

> [!CAUTION]
> The end-to-end integrity acceptance suite needs its own disposable PostgreSQL, object store, and local chain. Follow the isolated test steps in the user guide. **Never run its tamper checks against your regular database or Amoy.**

## Operations

Create encrypted object-storage and PostgreSQL backups with `scripts/backup_project.py`. Restores require explicit confirmation and are documented in the user guide.

## Documentation

- [User guide](docs/user-guide.md)
- [Reporter workflow](docs/reporter-workflow.md)
- [Local demo accounts and roles](docs/demo-accounts.md)
- [Integrity API contract](docs/integrity-api.md)
- [AI behavior and limitations](docs/ai-behavior.md)
- [Evaluation protocol](docs/evaluation-protocol.md)
- [Merkle specification](docs/merkle-spec.md)
- [Demo script](docs/demo-script.md)
