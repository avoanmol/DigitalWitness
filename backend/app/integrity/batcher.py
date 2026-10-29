from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Callable, TypedDict

from .chain import SubmissionUnknown, TransactionReverted, anchor_root, submit_root, wait_for_anchor
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
    chain_batch_id: int
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
    chain_batch_id: int
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
        "chain_batch_id": int(result["chain_batch_id"]),
        "root": root,
        "leaf_count": len(file_sha256_hexes),
        "transaction_hash": str(result["transaction_hash"]),
        "block_number": int(result["block_number"]),
        "chain_id": int(result["chain_id"]),
        "proofs": proofs,
    }


def prepare_evidence_records(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], dict[str, Any]]:
    """Build a deterministic root and proofs without making a chain call."""
    if not records:
        raise ValueError("at least one evidence record is required")
    if any(record.get("status") != "stored" for record in records):
        raise ValueError("only evidence with status 'stored' can be batched")

    ordered = sorted(
        records,
        key=lambda record: (_as_utc(record["uploaded_at"]), str(record["id"])),
    )
    identifiers = [str(record["id"]) for record in ordered]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("evidence_id values must be unique within a batch")

    levels = build_levels([record["sha256"] for record in ordered])
    root = "0x" + levels[-1][0].hex()
    evidence_proofs: list[EvidenceRecordProof] = [
        {
            "evidence_id": record["id"],
            "leaf_hash": leaf_hash(record["sha256"]).hex(),
            "leaf_index": index,
            "siblings": get_proof(levels, index),
        }
        for index, record in enumerate(ordered)
    ]
    return ordered, {
        "root": root,
        "leaf_count": len(ordered),
        "evidence_proofs": evidence_proofs,
    }


def anchor_evidence_records(
    records: Sequence[Mapping[str, Any]],
) -> AnchoredEvidenceRecords:
    """Legacy synchronous helper; staged database flows use the service below."""
    _, prepared = prepare_evidence_records(records)
    result = anchor_root(prepared["root"], prepared["leaf_count"])
    return {
        "chain_batch_id": int(result["chain_batch_id"]),
        "root": prepared["root"],
        "leaf_count": prepared["leaf_count"],
        "transaction_hash": str(result["transaction_hash"]),
        "block_number": int(result["block_number"]),
        "chain_id": int(result["chain_id"]),
        "evidence_proofs": prepared["evidence_proofs"],
    }


class PersistedAnchoredEvidenceRecords(AnchoredEvidenceRecords):
    batch_id: str


def anchor_persisted_evidence_records(
    records: Sequence[Mapping[str, Any]],
    session_factory: Callable[[], Any],
) -> PersistedAnchoredEvidenceRecords:
    """Persist building/proof state, submit, persist tx, then confirm and anchor.

    This service owns each short DB transaction so the building and submitted
    states are durable while chain submission and confirmation polling run. If
    submission fails definitively, evidence is released for retry. Uncertain
    broadcasts and submitted transactions retain their proofs for recovery.
    """
    from .persistence import (
        confirm_submitted_batch,
        create_building_batch,
        mark_batch_submitted,
        mark_submitted_batch_failed,
    )

    ordered, prepared = prepare_evidence_records(records)
    batch_id = None
    persisted = False
    submission = None
    try:
        with session_factory() as session:
            batch = create_building_batch(
                session,
                root_hash=prepared["root"],
                records=ordered,
                evidence_proofs=prepared["evidence_proofs"],
            )
            batch_id = batch.id
            session.commit()
            persisted = True

        submission = submit_root(prepared["root"], prepared["leaf_count"])
        with session_factory() as session:
            mark_batch_submitted(
                session,
                batch_id=batch_id,
                transaction_hash=submission["transaction_hash"],
                chain_id=submission["chain_id"],
            )
            session.commit()

        receipt = wait_for_anchor(
            submission, prepared["root"], prepared["leaf_count"]
        )
        with session_factory() as session:
            batch = confirm_submitted_batch(
                session, batch_id=batch_id, anchor_receipt=receipt
            )
            session.commit()

        return {
            "batch_id": str(batch_id),
            "chain_batch_id": int(receipt["chain_batch_id"]),
            "root": prepared["root"],
            "leaf_count": prepared["leaf_count"],
            "transaction_hash": receipt["transaction_hash"],
            "block_number": int(receipt["block_number"]),
            "chain_id": int(receipt["chain_id"]),
            "evidence_proofs": prepared["evidence_proofs"],
        }
    except Exception as exc:
        if persisted and batch_id is not None and (
            isinstance(exc, TransactionReverted)
            or (submission is None and not isinstance(exc, SubmissionUnknown))
        ):
            try:
                with session_factory() as session:
                    mark_submitted_batch_failed(
                        session,
                        batch_id=batch_id,
                        failure_code=(
                            "transaction_reverted"
                            if isinstance(exc, TransactionReverted)
                            else "submission_failed"
                        ),
                    )
                    session.commit()
            except Exception as failure_error:
                exc.add_note(
                    "Could not persist failed/retryable batch state: "
                    + str(failure_error)
                )
        elif persisted and submission is not None:
            # Also recover a DB outage immediately after broadcast when possible.
            try:
                with session_factory() as session:
                    mark_batch_submitted(session, batch_id=batch_id, **submission)
                    session.commit()
            except Exception:
                exc.add_note("Batch retained for reconciliation; do not submit its evidence again.")
        raise
