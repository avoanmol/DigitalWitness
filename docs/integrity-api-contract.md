# Integrity API contract proposal for B and D

This is A's proposal for the shared API contract. B owns the FastAPI router,
authentication, authorization, audit logging, and the canonical
docs/api-contract.md. These shapes can be copied there when that file is ready.

All timestamps are UTC ISO 8601 strings ending in Z. Hashes are 64 lowercase
hexadecimal characters without 0x. Roots and transaction hashes are
0x-prefixed lowercase hex. The API batch_id is the database UUID; chain_batch_id
is the uint256 identifier emitted by the contract.

## POST /evidence/{evidence_id}/verify

Allowed roles: reporter for own evidence; investigator, legal, and admin.

Return HTTP 200 with one of the guide's exact result values:

- verified: Unchanged since anchoring on [date and time]. This does not prove the file was genuine before upload.
- altered: This file no longer matches what was recorded and anchored. Do not rely on it.
- pending: Not anchored yet. The file is stored and hashed; anchoring is queued.
- error: Verification could not be completed (reason shown). Try again; this is not a finding about the file.

Response fields:

    {
      "evidence_id": "uuid",
      "result": "verified | altered | pending | error",
      "message": "human-readable status",
      "expected_hash": "64 lowercase hex or null",
      "recomputed_hash": "64 lowercase hex or null",
      "onchain_root": "0x... or null",
      "computed_root": "0x... or null",
      "tx_hash": "0x... or null",
      "batch_id": "database uuid or null",
      "checked_at": "UTC ISO 8601 timestamp"
    }

A verification attempt is stored and appended to B's audit log. RPC or storage
failures produce error, never altered.

## GET /evidence/{evidence_id}/proof

Allowed roles: same as verify. Viewing the proof is audited.

    {
      "evidence_id": "uuid",
      "batch_id": "database uuid",
      "leaf_index": 3,
      "leaf_hash": "64 lowercase hex",
      "proof": [
        {"hash": "64 lowercase hex", "side": "left"},
        {"hash": "64 lowercase hex", "side": "right"}
      ],
      "root": "0x...",
      "tx_hash": "0x...",
      "chain_id": 80002,
      "explorer_url": "network-specific transaction URL"
    }

When no proof exists, return the pending representation agreed in B's canonical
API contract; never report this as altered.

## GET /batches/{batch_id}

Allowed roles: investigator, legal, and admin.

    {
      "id": "database uuid",
      "chain_batch_id": "uint256 encoded as a decimal string",
      "root_hash": "0x...",
      "leaf_count": 10,
      "tx_hash": "0x...",
      "chain_id": 80002,
      "block_number": 123456,
      "status": "building | submitted | confirmed | failed",
      "created_at": "UTC ISO 8601 timestamp",
      "anchored_at": "UTC ISO 8601 timestamp or null"
    }

Errors use the shared shape:
{"error": {"code": "string", "message": "human text", "details": {}}}.

