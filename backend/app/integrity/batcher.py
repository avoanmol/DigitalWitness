from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, TypedDict

from .chain import anchor_root
from .merkle import ProofStep, build_levels, get_proof, leaf_hash


DEFAULT_ANCHOR_BATCH_SIZE = 10
DEFAULT_ANCHOR_INTERVAL_SECONDS = 30
RETRY_BACKOFF_SECONDS = (5, 15, 45)


class EvidenceProof(TypedDict):
    file_sha256_hex: str
    leaf_hash: str
    leaf_index: int
    siblings: list[ProofStep]


class AnchoredBatch(TypedDict):
    batch_id: int
    root: str
    leaf_count: int
    transaction_hash: str
    block_number: int
    chain_id: int
    proofs: list[EvidenceProof]


class EvidenceRecordProof(TypedDict):
    evidence_id: Any
    leaf_hash: str
    leaf_index: int
    siblings: list[ProofStep]


class AnchoredEvidenceRecords(TypedDict):
    batch_id: int
    root: str
    leaf_count: int
    transaction_hash: str
    block_number: int
    chain_id: int
    evidence_proofs: list[EvidenceRecordProof]


def retry_delay_after_failure(failed_attempts: int) -> int | None:
    """Return the guide's delay for a retry, or None after the last retry."""
    if failed_attempts < 1:
        raise ValueError("failed_attempts must be at least 1")
    if failed_attempts > len(RETRY_BACKOFF_SECONDS):
        return None
    return RETRY_BACKOFF_SECONDS[failed_attempts - 1]


def _as_utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("uploaded_at must be a timezone-aware UTC timestamp")
    return value.astimezone(timezone.utc)


def should_trigger_batch(
    candidates: Sequence[Mapping[str, Any]],
    now: datetime,
    batch_size: int | None = None,
    interval_seconds: int | None = None,
) -> bool:
    """Apply size or age threshold to candidates already filtered by the DB."""
    try:
        batch_size = (
            int(os.environ.get("ANCHOR_BATCH_SIZE", DEFAULT_ANCHOR_BATCH_SIZE))
            if batch_size is None
            else batch_size
        )
        interval_seconds = (
            int(os.environ.get("ANCHOR_INTERVAL_SECONDS", DEFAULT_ANCHOR_INTERVAL_SECONDS))
            if interval_seconds is None
            else interval_seconds
        )
    except ValueError as exc:
        raise ValueError("anchor batch settings must be integers") from exc
    if batch_size < 1 or interval_seconds < 0:
        raise ValueError("batch_size must be positive and interval_seconds nonnegative")
    if not candidates:
        return False
    if len(candidates) >= batch_size:
        return True

    current_time = _as_utc(now)
    oldest_upload = min(_as_utc(row["uploaded_at"]) for row in candidates)
    return (current_time - oldest_upload).total_seconds() >= interval_seconds


def anchor_hash_batch(file_sha256_hexes: Sequence[str]) -> AnchoredBatch:
    """Build and anchor hashes that are already in evidence order."""
    if not file_sha256_hexes:
        raise ValueError("at least one file hash is required")

    levels = build_levels(file_sha256_hexes)
    root = "0x" + levels[-1][0].hex()
    result = anchor_root(root, len(file_sha256_hexes))

    proofs: list[EvidenceProof] = [
        {
            "file_sha256_hex": file_hash,
            "leaf_hash": leaf_hash(file_hash).hex(),
            "leaf_index": index,
            "siblings": get_proof(levels, index),
        }
        for index, file_hash in enumerate(file_sha256_hexes)
    ]

    return {
        "batch_id": int(result["batch_id"]),
        "root": root,
        "leaf_count": len(file_sha256_hexes),
        "transaction_hash": str(result["transaction_hash"]),
        "block_number": int(result["block_number"]),
        "chain_id": int(result["chain_id"]),
        "proofs": proofs,
    }


def anchor_evidence_records(
    records: Sequence[Mapping[str, Any]],
) -> AnchoredEvidenceRecords:
    """Sort guide-shaped records, anchor them, and associate proofs by evidence ID."""
    if not records:
        raise ValueError("at least one evidence record is required")

    ordered = sorted(
        records,
        key=lambda record: (
            _as_utc(record["uploaded_at"]),
            str(record["evidence_id"]),
        ),
    )
    identifiers = [str(record["evidence_id"]) for record in ordered]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("evidence_id values must be unique within a batch")

    batch = anchor_hash_batch(
        [record["file_sha256_hex"] for record in ordered]
    )

    evidence_proofs: list[EvidenceRecordProof] = [
        {
            "evidence_id": record["evidence_id"],
            "leaf_hash": proof["leaf_hash"],
            "leaf_index": proof["leaf_index"],
            "siblings": proof["siblings"],
        }
        for record, proof in zip(ordered, batch["proofs"], strict=True)
    ]

    return {
        "batch_id": batch["batch_id"],
        "root": batch["root"],
        "leaf_count": batch["leaf_count"],
        "transaction_hash": batch["transaction_hash"],
        "block_number": batch["block_number"],
        "chain_id": batch["chain_id"],
        "evidence_proofs": evidence_proofs,
    }

