# DigitalWitness user guide

## Start the complete local website

From the repository root, copy `.env.example` to `.env` once, generate local secrets, and configure `CHAIN_EXPECTED_ID=80002`, the Amoy RPC, funded test wallet, deployed contract address, and matching sender address. The application rejects a mismatched chain ID before sending. Keep `.env` private. Then run:

```powershell
docker compose up --build -d
docker compose ps
```

Open [http://localhost:3000](http://localhost:3000) for the website and [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the API. The stack starts PostgreSQL, Silo object storage, FastAPI, the Next.js website, the integrity worker, and the AI worker. For the judge demo, the integrity worker must be configured for Polygon Amoy. A local Hardhat chain is available only as an isolated development/test fallback.

The website starts in synthetic mock mode. To use the real API, set `NEXT_PUBLIC_USE_MOCK=false` in `.env` and rebuild the web service. New signups are reporters. To create the first admin interactively, run `docker compose exec -it api python -m backend.bootstrap_admin admin@example.test --name "Workspace Admin"`; choose a strong password in the prompt. Admins can then assign investigator and legal roles from **User accounts**. Tokens stay in browser memory and are cleared on reload or sign-out.

## Submit and inspect evidence

Reporters can create a case and upload JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV, or WEBM files up to 100 MB. MP4, MOV, and WEBM analysis samples at most four frames from videos no longer than 60 seconds. Audio is preserved, but transcription is not enabled by default. The API checks file signatures, computes SHA-256 from the uploaded bytes, encrypts the original with AES-256-GCM, stores it in Silo, and returns a canonical HMAC-signed receipt.

Use the receipt screen to save the JSON and confirm the server signature. Open an evidence record to preview/download the original, view the receipt, see AI extraction coverage, and run an integrity check. A status of `pending` means anchoring or verification has not completed. `error` means a required service was unavailable. `altered` means the current stored bytes or proof do not match the recorded fingerprint. The result does not establish authorship or truth.

## Prepare a complaint draft

From one of your own cases, choose **Prepare complaint draft**. Add only the incident details needed to explain what happened, review the case evidence and any case-linked AI notes, then confirm both review checkboxes to download the packet. The form does not request Aadhaar, passwords, or a full home address. The statement is used to generate the download and is not saved in the database or audit trail; the audit event records only the packet hash, selected channel, format, and record counts.

When the entered statement or case notes contain characters the built-in PDF font cannot represent, the download switches to a UTF-8 text file so the wording is preserved. Open and review that text before using it on the official form.

The PDF is a draft, not an FIR, legal finding, or authenticity verdict. It does not contain the original evidence files; provide those separately if the official channel requests them. DigitalWitness never submits the complaint. After downloading, you can choose to open the official [National Cyber Crime Reporting Portal](https://www.cybercrime.gov.in/) or take the draft and original files to local police. The portal may ask for identity or contact details depending on the reporting route; provide them directly to the official service only if you choose to continue.

## Investigate and review

Investigators can view cases, analysis, extracted entities, suggested links, flags, and a deterministic case summary. Legal users have read-only case and review access. Investigators and admins can confirm or reject AI flags and case links; each flag review requires a reason. Admins manage account roles and activation. Legal and admin users can inspect the audit trail and run its hash-chain check. The API enforces every role; hiding a screen is not the security boundary.

The PDF report includes case metadata, evidence hashes, current anchor/verification status, human-confirmed flags and links, and custody/audit details. Keep reports private and verify the audit chain separately when needed.

## AI and media-authenticity limits

The five focus categories are cyberstalking/bullying, blackmail/threats, intimate-image abuse, defamation/morphing, and fake-profile impersonation. They are review categories, not crime predictions. OCR and phrase/entity rules can miss context, languages, or altered content. Metadata, OCR, sampled frames, and optional model output cannot prove that a screenshot or video is genuine or fake. There is no validated deepfake detector or real-world accuracy claim in this build. Use only consented, de-identified evaluation material and keep the challenge set held out from tuning.

## Synthetic demo examples

To seed six synthetic text examples and four role accounts, set `DW_ENABLE_SYNTHETIC_SEED=true` and a private `DW_DEMO_PASSWORD` (12+ characters) in a **fresh development `.env`**, and run `docker compose exec api python -m backend.seed_demo`. The seed contains five focus categories and a benign negative example. Do not run it against a production database or an Amoy-connected worker: the integrity worker will submit eligible roots and use test-token funds.

## Backups

With the stack running, create a timestamped PostgreSQL and encrypted-object backup from the repo root:

```powershell
& .\backend\.venv\Scripts\python.exe scripts\backup_project.py
```

Keep the resulting `backups/` folder private and store a separate secure copy of `.env`. Restore only after making another backup; `scripts/restore_project.py` requires an explicit database-replacement flag, a typed confirmation, and refuses object overwrites unless separately allowed. Test restores against a disposable stack before relying on them.

## Tests and development checks

```powershell
.\node_modules\.bin\hardhat.cmd test
& .\backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
& .\backend\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
Set-Location frontend
npm run lint
npm run typecheck
npm run build
```

The separate `compose.integrity-test.yml` acceptance stack is disposable and uses synthetic records only. It checks both the background AI review flow and end-to-end integrity/tamper behavior. Do not point it at the working database or real evidence.

From the repository root, run:

```powershell
docker compose -f compose.integrity-test.yml --profile checks up --build -d api ai-worker
docker compose -f compose.integrity-test.yml --profile checks run --rm --no-deps checks python scripts/ai_acceptance.py
docker compose -f compose.integrity-test.yml --profile checks run --rm --no-deps checks python scripts/integrity_acceptance.py
docker compose -f compose.integrity-test.yml stop chain
docker compose -f compose.integrity-test.yml --profile checks run --rm --no-deps checks python scripts/integrity_acceptance.py --outage
docker compose -f compose.integrity-test.yml down
```

The AI check covers reporter registration/login/profile and case creation, background text analysis, entity matching across two synthetic cases, a pending source-linked flag, case summary, investigator review, role-protected PDF report generation, and reporter-owned complaint packet preview/download. The integrity check writes `docs/integrity-validation.json` with ten local Hardhat timings. Both checks run against temporary test services, not Amoy or the regular database.
