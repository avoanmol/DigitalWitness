# DigitalWitness Merkle Specification

Status: A-side Merkle, local contract, chain connector, batch ordering, and
proof verification are implemented. Database-backed worker transactions,
API endpoints, and running-stack tamper tests require B's shared models,
storage, audit, and worker services.

## 1. Purpose

Create a verifiable integrity record for a batch of digital evidence.
The Merkle tree is built off-chain. Only the Merkle root and leaf count
may be stored on-chain.

## 2. File hashing

B computes SHA-256 over the original file bytes while streaming the upload,
before encryption or other processing. Represent the digest as 64 lowercase
hexadecimal characters. A's Merkle module converts it to 32 raw bytes before
computing the leaf.

## 3. Leaf hashing

leaf_hash = SHA-256(0x00 || raw_32_byte_file_hash)

The 0x00 prefix separates leaf hashing from parent hashing.

## 4. Parent hashing

parent_hash = SHA-256(0x01 || left_hash || right_hash)

The 0x01 prefix separates parent hashing from leaf hashing.
The left and right child order must be preserved.

## 5. Odd number of nodes

If a level has an unpaired final node, promote it unchanged to the
next level. Do not duplicate it. One leaf is its own root.

## 6. Evidence ordering

Order evidence by uploaded_at ascending, then evidence_id ascending.
anchor_evidence_records normalizes timezone-aware values to UTC and applies
that ordering before building the tree and proofs. B's database query must
use the same ordering.

## 7. Merkle proofs

Persist the zero-based leaf index and ordered sibling hashes, including
whether each sibling is on the left or right. A level with no sibling adds
no proof step.

## 8. On-chain privacy

Store only the Merkle root and leaf count on-chain. Do not store filenames,
case details, personal information, individual file hashes, or evidence
content on-chain.

## 9. Verification semantics

A successful proof establishes that the supplied file hash matches the
anchored Merkle leaf. It does not establish that the evidence was authentic
before it was uploaded or anchored.

Verification results use exactly verified, altered, pending, and error.
Chain or storage failures are error, never altered.

## 10. Required tests

- Empty input handling
- A single leaf
- Two leaves
- An odd number of leaves
- Proof verification for each leaf in trees of 1, 2, 3, 4, 5, 7, and 8 leaves
- Invalid proof rejection
- Modified file detection
- Consistent evidence ordering

## 11. Backend coordination

B owns the shared backend, database migrations, object storage, audit service,
and worker loop. A supplies the proposed table contract in
docs/integrity-db-contract.md. B adds those tables to the existing Alembic
history. Integrity code must not create an independent migration history.

## 12. Local and testnet chain settings

Local development uses the Hardhat node at http://127.0.0.1:8545 with one
confirmation and an unlocked Hardhat sender account. Polygon Amoy uses
AMOY_RPC_URL and AMOY_PRIVATE_KEY, chain ID 80002, and two confirmations.
Never use the printed Hardhat accounts or their public test keys on a live
network.
