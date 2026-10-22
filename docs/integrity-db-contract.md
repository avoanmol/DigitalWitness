# Integrity database contract alignment

This document maps Member A's integrity services to the shared schema described in `DigitalWitness_Database_Schema.pdf`. The PDF reports that the shared Alembic migration is applied and includes the tables below. It is a readable reference, not the DDL source of truth; use the actual Alembic migration and models for exact types, nullability, constraints, and indexes. Member A does not create a separate migration history.

## Existing shared records

- `evidence`: use `id`, `sha256`, `status`, and `uploaded_at`. The worker selects only `status = 'stored'` evidence that has no `merkle_proofs` row. The stored digest is 64 lowercase hex characters without `0x`.
- `jobs`: enqueue work with `type = 'anchor'` and the schema's existing `queued`, `running`, `done`, and `failed` lifecycle. Use `attempts`, `max_attempts`, `run_after`, and `last_error` for retry handling. Apply the guide's 5, 15, and 45 second retry delays through `run_after`.

## `merkle_batches`

| Schema field | Integrity use |
| --- | --- |
| `id` | Database UUID primary key; API `batch_id` |
| `chain_batch_id` | Nullable on-chain uint256 returned by `RootAnchored`; distinct from `id` |
| `root_hash` | Merkle root; store `0x` plus 64 lowercase hex characters |
| `leaf_count` | Number of evidence leaves in the batch |
| `tx_hash` | Nullable transaction hash |
| `chain_id` | Blockchain network identifier |
| `block_number` | Nullable receipt block number |
| `status` | `building`, `submitted`, `confirmed`, or `failed` |
| `created_at`, `anchored_at` | UTC timestamps; `anchored_at` remains null until confirmed |

## `merkle_proofs`

- `evidence_id` is the primary key and a restricted foreign key to `evidence.id`.
- `batch_id` references `merkle_batches.id`; it is a database UUID, not the on-chain ID.
- `leaf_index` is zero-based and unique within a batch.
- `leaf_hash` is 64 lowercase hex characters without `0x`.
- `proof` is JSONB containing ordered `{ "hash": "<64 lowercase hex>", "side": "left" | "right" }` entries.

The worker sorts by `evidence.uploaded_at ASC, evidence.id ASC`. `batcher.anchor_evidence_records` accepts the schema-shaped fields `id`, `sha256`, `status`, and `uploaded_at`, and returns `evidence_id`, `leaf_index`, `leaf_hash`, and proof data.

## `verifications`

Store every attempt with `id`, `evidence_id`, nullable `requested_by`, `result`, nullable `recomputed_hash`, `expected_hash`, `computed_root`, `onchain_root`, nullable `reason`, and `checked_at`. Results are exactly `verified`, `altered`, `pending`, or `error`. Storage and RPC failures are `error`, never `altered`.

## Persistence handoff

Persist a building batch and its proof rows using the shared transaction and job infrastructure. After the chain transaction reaches the required confirmation count, save `chain_batch_id`, transaction hash, chain ID, block number, and `anchored_at`, then mark the batch confirmed and evidence anchored. A failed or unconfirmed chain operation must not create verified proofs or mark evidence altered; leave retry and failure handling to the shared jobs policy.
