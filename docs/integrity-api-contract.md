# Integrity and API contract

The API uses the shared FastAPI authentication, case-access policy, append-only audit log, and Alembic schema. Reporters can access their own cases; investigators, legal reviewers, and admins can access case evidence. Only legal and admin roles can read the audit trail. Only admins can manage user accounts.

Timestamps are UTC ISO 8601 strings. Hashes are 64 lowercase hexadecimal characters. Merkle roots and transaction hashes are 0x-prefixed. The API batch ID is a database UUID; the chain batch ID is the contract uint256 represented as a decimal string.

## Upload and receipts

POST /evidence/upload accepts one multipart file, a case_id query parameter, and optional investigation_categories. Allowed types are JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV, and WEBM. Maximum size defaults to 100 MB.

The server validates the content signature where the format has one, computes SHA-256 from the exact uploaded bytes, encrypts the original with AES-256-GCM, stores it in the private Silo bucket, and returns receipt fields plus a canonical HMAC-SHA-256 signature. Audio is stored without default transcription. Video sampling is limited to four frames from clips no longer than 60 seconds.

GET /evidence/{evidence_id}/file returns the authenticated original bytes and records the access in the audit log. GET /evidence/{evidence_id}/receipt returns the signed upload snapshot and signature_valid. Both responses are private and non-cacheable.

## POST /evidence/{evidence_id}/verify

Allowed roles: reporter for their own evidence; investigator, legal, and admin.

The result is one of verified, altered, pending, or error:

- verified means the current stored bytes match the uploaded fingerprint and confirmed chain proof.
- altered means the bytes or saved Merkle proof do not match the anchored record.
- pending means the record has not been anchored or confirmed.
- error means required storage or chain services were unavailable. It is not an alteration result.

The response contains evidence_id, result, message, expected_hash, recomputed_hash, onchain_root, computed_root, tx_hash, batch_id, chain_batch_id, and checked_at. Attempts are stored and audited. RPC or storage failures return error, never altered.

Case and evidence summaries also use `not_checked` when an anchor is confirmed but a stored-file integrity check has not completed since anchoring. This is a display state, not a persisted verification result. A previously saved `pending` check becomes `not_checked` in these summaries after its batch confirms.

## Proof and batch reads

GET /evidence/{evidence_id}/proof returns the saved Merkle proof after case authorization and audits the read. A record without a confirmed proof is pending; it is never called altered for that reason.

GET /batches/{batch_id} is investigator/legal/admin only and returns the database UUID, chain batch ID, root, leaf count, transaction hash, chain ID, block number, status, and timestamps.

## Audit and admin routes

GET /audit is limited to legal/admin and supports case_id, limit (1–500, default 200), and offset.

GET /audit/verify checks the full hash chain and appends an audit record for the check. New audit hashes cover sequence, timestamp, and event fields. Existing entries written with the earlier hash format remain verifiable for local-history compatibility.

GET /admin/users and PATCH /admin/users/{user_id} are admin-only. The API prevents an admin from disabling or demoting their own account and prevents removing the last active administrator. All role and activation changes are audited.

## Error response

HTTP and request-validation errors use:

    {"error":{"code":"string","message":"human text","details":{}}}

Validation details omit submitted values. This avoids echoing passwords and evidence data. The frontend also understands legacy FastAPI detail responses.
