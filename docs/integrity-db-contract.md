# Integrity database contract for B

Status: proposal for B to incorporate into the shared Alembic migration chain.
This file defines A-owned data needs only; it does not create migrations.

The names and relationships below follow the team guide. The evidence table
remains B-owned and is assumed to expose id, sha256, status, and uploaded_at.
B owns all migrations and resolves final column types and constraints with A.

## merkle_batches

| Column | Suggested type | Requirements |
| --- | --- | --- |
| id | UUID | Primary key, generated UUID v4 |
| chain_batch_id | NUMERIC(78, 0), nullable | uint256 from RootAnchored; unique with chain_id after confirmation |
| root_hash | CHAR(66) | Lowercase 0x plus 64 hex characters |
| leaf_count | BIGINT | Between 1 and 4,294,967,295 |
| tx_hash | CHAR(66), nullable | Transaction hash |
| chain_id | BIGINT | Network identifier |
| block_number | BIGINT, nullable | Receipt block |
| status | TEXT | building, submitted, confirmed, or failed |
| created_at | TIMESTAMPTZ | UTC, default current time |
| anchored_at | TIMESTAMPTZ, nullable | Time from the confirmed batch |

Indexes: (status, created_at) for worker candidate processing; unique
(chain_id, chain_batch_id) when chain_batch_id is present.

## merkle_proofs

| Column | Suggested type | Requirements |
| --- | --- | --- |
| evidence_id | UUID | Unique FK to evidence.id, delete restricted |
| batch_id | UUID | FK to merkle_batches.id, delete restricted |
| leaf_index | BIGINT | Zero-based index in the ordered batch |
| leaf_hash | CHAR(64) | Lowercase digest without 0x |
| proof | JSONB | Ordered array; hash is 64 lowercase hex without 0x, side is left or right |

The worker orders candidates by uploaded_at ASC, evidence.id ASC. It stores
that order in leaf_index and uses it to construct each proof.

## verifications

| Column | Suggested type | Requirements |
| --- | --- | --- |
| id | UUID | Primary key, generated UUID v4 |
| evidence_id | UUID | FK to evidence.id, delete restricted |
| requested_by | UUID, nullable | Requesting user FK where available |
| result | TEXT | verified, altered, pending, or error |
| recomputed_hash | CHAR(64), nullable | Lowercase digest without 0x |
| expected_hash | CHAR(64), nullable | Upload-time digest without 0x |
| computed_root | CHAR(66), nullable | Lowercase root with 0x |
| onchain_root | CHAR(66), nullable | Lowercase root with 0x |
| reason | TEXT, nullable | Human-readable explanation |
| checked_at | TIMESTAMPTZ | UTC, default current time |

## Worker handoff

A selects evidence rows with status stored and no proof, ordered by
uploaded_at, id, using B's shared job and row-locking infrastructure.
A returns the confirmed transaction hash, chain batch ID, chain ID, block,
leaf count, root, and each evidence_id, leaf_index, leaf_hash, and proof.
B's migration and transaction code persists those values and updates evidence
status; A does not create a separate migration chain.

A failed or unconfirmed RPC result must not mark evidence altered.
Verification returns pending without a proof, altered for a mismatch,
and error when the chain or storage cannot be checked.

