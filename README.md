# DigitalWitness

DigitalWitness is a case-based evidence preservation and investigation demo. It records an upload's SHA-256 fingerprint, encrypts the original file in object storage, issues a signed receipt, and anchors batches of fingerprints to Polygon Amoy. Its OCR, entity matching, and harassment-category suggestions are investigative leads for human review; they do not determine truth, guilt, or whether media is authentic.

## Run locally

Requirements: Docker Desktop, Git, and (for tests) Node.js 20.9+ and Python 3.11.

1. Copy `.env.example` to `.env` and replace the local secret placeholders. Set `CHAIN_EXPECTED_ID=80002`, `CHAIN_RPC_URL`, `CHAIN_CONTRACT_ADDRESS`, and `CHAIN_SENDER_ADDRESS` for the Polygon Amoy deployment/wallet you intend to demo. The app refuses to submit if the RPC reports a different chain. Put the wallet signing key in `.env` only. Never commit `.env` or use a funded wallet's key in a public repository.
2. Set `NEXT_PUBLIC_USE_MOCK=false` for the live API flow. Leave `LLM_ENABLED=false` unless the chosen provider is approved for the evidence you submit.
3. Start the services:

```powershell
docker compose up --build -d
docker compose ps
```

Open the website at [http://localhost:3000](http://localhost:3000) and the API reference at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Compose starts PostgreSQL, Silo-compatible object storage, FastAPI, the Next.js website, an integrity worker, and an AI analysis worker. New registrations are reporters. Create the first administrator with `docker compose exec -it api python -m backend.bootstrap_admin admin@example.test --name "Workspace Admin"`, then assign investigator/legal roles from the admin page.

The website is built with mock mode on by default. Change the setting in `.env` and rebuild the web service to enable real API calls. `scripts/setup_local_env.py` generates local application secrets if `.env` does not exist.

## Evidence and investigation

The API accepts JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV, and WEBM files up to 100 MB. It checks supported file signatures, hashes the original bytes, encrypts evidence with AES-256-GCM, and stores it outside the database. A canonical HMAC-signed receipt records the upload fingerprint and custody identifiers. Investigators can review OCR/extraction coverage, five configurable harassment focus categories, entities, suggested case links, and threat flags. Human decisions are required for link/flag review. Admin and legal roles can inspect and verify the append-only audit chain; admins manage accounts.

Video analysis samples at most four frames from videos up to 60 seconds. Audio is preserved but is not transcribed. Metadata, OCR, sparse frames, and optional model output cannot prove that a screenshot or video is real or fake. The project has no validated deepfake detector or demonstrated real-world accuracy claim. Use synthetic or consented, de-identified evidence only.

## Chain configuration

The judge demo uses Polygon Amoy (chain ID 80002). `CHAIN_EXPECTED_ID` defaults to 80002 and is checked before the worker broadcasts; `CHAIN_CONTRACT_ADDRESS` must be the `EvidenceAnchor` deployment on that same RPC, and the sender must match the signing wallet and have test POL for gas. A localhost Hardhat chain is available only through the explicit `compose.local-chain.yml` development profile, which overrides the expected ID to 31337. It is disposable and its transactions are not Amoy transactions. Do not point an existing database with confirmed batches at a freshly reset local chain.

Only each Merkle root and leaf count are written on-chain. Evidence, personal details, and individual file hashes remain off-chain. The tree hashes leaves as `SHA-256(0x00 || file_hash)`, parents as `SHA-256(0x01 || left || right)`, and promotes an unpaired node unchanged. Verification failures caused by unavailable storage/RPC return `error`; they are not labeled `altered`.

## Checks

```powershell
.\node_modules\.bin\hardhat.cmd test
& .\backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
& .\backend\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
Set-Location frontend
npm run lint
npm run typecheck
npm run build
```

The end-to-end integrity acceptance suite uses a separate disposable PostgreSQL, object store, and local chain. Follow the isolated test steps in [the user guide](docs/user-guide.md); do not run its tamper checks against the regular database or Amoy.

## Operations and references

Create encrypted object and PostgreSQL backups with `scripts/backup_project.py`; restore requires explicit confirmation and is documented in the user guide. See [user guide](docs/user-guide.md), [integrity API contract](docs/integrity-api-contract.md), [AI behavior and limitations](docs/ai-spec.md), [evaluation protocol](docs/ai-evaluation.md), [Merkle specification](docs/merkle-spec.md), and [demo script](docs/demo-script.md).
## Reporter and demo guides

- [Reporter workflow](docs/reporter-workflow.md)
- [Local demo accounts and roles](docs/demo-accounts.md)
