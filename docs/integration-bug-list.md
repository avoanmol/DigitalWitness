# Integration status

Use only synthetic evidence in local integration checks. Never paste names, access tokens, file contents, or RPC secrets into this document.

| ID | Area | Implemented behavior | Verification status |
| --- | --- | --- | --- |
| D-001 | Case/evidence reads | Scoped case list/detail, authenticated encrypted-file preview/download, canonical receipt retrieval, proof, and verify routes | Backend acceptance check runs against isolated PostgreSQL, Silo, and Hardhat services |
| D-002 | AI review | Background OCR/rules analysis, normalized entities, suggested links, investigator review, deterministic summaries, and feedback counts | Synthetic unit cases pass; run the disposable integration stack before a demo |
| D-003 | Audit | Legal/admin list and verify endpoints; hash includes sequence and timestamp for new entries; legacy entries remain verifiable; evidence reads are audited | Unit chain tests pass; disposable HTTP acceptance includes audit access checks |
| D-004 | Reporter formats | JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV, and WEBM up to 100 MB; server checks supported signatures and hashes original bytes | Signature unit tests pass; audio is preserved without default transcription; video sampling remains bounded |
| D-005 | Browser CORS | Configurable allowlist for the local website origin; only required request headers are allowed | Local preflight was previously verified; recheck after changing `CORS_ORIGINS` |
| D-006 | Admin roles | First admin bootstrapped interactively; admin-only list/update endpoints and page; last/self admin protection | Unit/API acceptance coverage in the isolated stack |
| D-007 | Backups | PostgreSQL custom dump plus checksummed encrypted-object archive; guarded restore flow | Archive checksums and overwrite guard have unit coverage; perform a disposable restore rehearsal before production use |

The browser enforces role-based navigation for clarity, while FastAPI remains authoritative. The integration stack is disposable, uses temporary database/object storage, and connects only to local Hardhat. It must not be used with real evidence or the Amoy-connected app database.
