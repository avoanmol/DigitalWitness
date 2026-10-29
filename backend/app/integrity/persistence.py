"""Persistence operations for staged Merkle anchor batches."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.integrity.chain import get_batch
from backend.app.integrity.merkle import leaf_hash, root_from_proof
from backend.audit import append_audit_event
from backend.models import Evidence, MerkleBatch, MerkleProof


_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ROOT_RE = re.compile(r"^0x[0-9a-f]{64}$")
_TX_RE = re.compile(r"^0x[0-9a-f]{64}$")


class IntegrityPersistenceError(ValueError):
    """Raised when a submitted batch cannot safely be confirmed in the DB."""


def _positive_int(value: Any, name: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        qualifier = "nonnegative" if allow_zero else "positive"
        raise IntegrityPersistenceError(f"{name} must be a {qualifier} integer")
    return value



def create_building_batch(
    session: Session,
    *,
    root_hash: str,
    records: Sequence[Mapping[str, Any]],
    evidence_proofs: Sequence[Mapping[str, Any]],
) -> MerkleBatch:
    """Persist a building batch and all proofs while locking eligible evidence."""
    if not isinstance(root_hash, str) or not _ROOT_RE.fullmatch(root_hash):
        raise IntegrityPersistenceError("root_hash must be a 0x-prefixed 32-byte hash")
    if not records or len(records) != len(evidence_proofs):
        raise IntegrityPersistenceError("a batch needs one proof for every evidence row")
    if len(records) > 0xFFFFFFFF:
        raise IntegrityPersistenceError("batch exceeds the contract leaf-count limit")

    try:
        evidence_ids = [UUID(str(record["id"])) for record in records]
    except (KeyError, TypeError, ValueError, AttributeError):
        raise IntegrityPersistenceError("each batch record needs a valid evidence ID") from None
    if len(set(evidence_ids)) != len(evidence_ids):
        raise IntegrityPersistenceError("evidence IDs must be unique within a batch")
    if [proof.get("evidence_id") for proof in evidence_proofs] != [
        record["id"] for record in records
    ]:
        raise IntegrityPersistenceError("proof order must match batch evidence order")
    if [proof.get("leaf_index") for proof in evidence_proofs] != list(range(len(records))):
        raise IntegrityPersistenceError("proof leaf indexes must be contiguous from zero")

    evidence_rows = session.scalars(
        select(Evidence)
        .where(Evidence.id.in_(evidence_ids))
        .order_by(Evidence.uploaded_at, Evidence.id)
        .with_for_update()
    ).all()
    if len(evidence_rows) != len(records):
        raise IntegrityPersistenceError("one or more batch evidence records do not exist")
    if [evidence.id for evidence in evidence_rows] != evidence_ids:
        raise IntegrityPersistenceError("records must be ordered by upload time then evidence ID")
    if any(evidence.status != "stored" for evidence in evidence_rows):
        raise IntegrityPersistenceError("only stored evidence can enter a building batch")

    existing_proof_ids = session.scalars(
        select(MerkleProof.evidence_id).where(MerkleProof.evidence_id.in_(evidence_ids))
    ).all()
    if existing_proof_ids:
        raise IntegrityPersistenceError("evidence already belongs to an unfinished or confirmed batch")

    for evidence, record, proof in zip(evidence_rows, records, evidence_proofs, strict=True):
        if record.get("sha256") != evidence.sha256:
            raise IntegrityPersistenceError("batch evidence hash changed before persistence")
        if not _HASH_RE.fullmatch(evidence.sha256):
            raise IntegrityPersistenceError("stored evidence hash is malformed")
        if leaf_hash(evidence.sha256).hex() != proof.get("leaf_hash"):
            raise IntegrityPersistenceError("proof leaf does not match the stored evidence hash")
        try:
            computed_root = "0x" + root_from_proof(evidence.sha256, proof.get("siblings", []))
        except (KeyError, TypeError, ValueError):
            raise IntegrityPersistenceError("prepared Merkle proof is malformed") from None
        if computed_root != root_hash:
            raise IntegrityPersistenceError("prepared Merkle proof does not match the root")

    batch = MerkleBatch(
        root_hash=root_hash,
        leaf_count=len(records),
        status="building",
    )
    session.add(batch)
    session.flush()
    session.add_all(
        [
            MerkleProof(
                evidence_id=evidence.id,
                batch_id=batch.id,
                leaf_index=proof["leaf_index"],
                leaf_hash=proof["leaf_hash"],
                proof=proof["siblings"],
            )
            for evidence, proof in zip(evidence_rows, evidence_proofs, strict=True)
        ]
    )
    session.flush()
    return batch


def mark_batch_submitted(
    session: Session,
    *,
    batch_id: UUID,
    transaction_hash: str,
    chain_id: int,
) -> MerkleBatch:
    """Persist the broadcast transaction before any confirmation polling."""
    if not isinstance(transaction_hash, str) or not _TX_RE.fullmatch(transaction_hash.lower()):
        raise IntegrityPersistenceError("transaction_hash must be a 0x-prefixed 32-byte hash")
    transaction_hash = transaction_hash.lower()
    chain_id = _positive_int(chain_id, "chain_id")

    batch = session.scalar(
        select(MerkleBatch).where(MerkleBatch.id == batch_id).with_for_update()
    )
    if batch is None:
        raise IntegrityPersistenceError("Merkle batch does not exist")
    if batch.status == "submitted":
        if batch.tx_hash == transaction_hash and batch.chain_id == chain_id:
            return batch
        raise IntegrityPersistenceError("submitted batch transaction cannot be changed")
    if batch.status != "building":
        raise IntegrityPersistenceError("only building batches can be submitted")

    batch.tx_hash = transaction_hash
    batch.chain_id = chain_id
    batch.status = "submitted"
    case_ids = session.scalars(
        select(Evidence.case_id)
        .join(MerkleProof, MerkleProof.evidence_id == Evidence.id)
        .where(MerkleProof.batch_id == batch.id)
    ).all()
    for case_id in sorted(set(case_ids), key=str):
        append_audit_event(
            session,
            action="anchor_submitted",
            target_type="merkle_batch",
            target_id=str(batch.id),
            case_id=case_id,
            details={"transaction_hash": transaction_hash, "chain_id": chain_id},
        )
    session.flush()
    return batch

def confirm_submitted_batch(
    session: Session,
    *,
    batch_id: UUID,
    anchor_receipt: Mapping[str, Any],
) -> MerkleBatch:
    """Move a submitted batch to confirmed after the chain connector confirms it.

    The caller must pass the receipt returned only after the configured
    confirmation depth. This function checks the contract's stored root/count,
    validates every persisted proof against its evidence hash, then stages the
    batch and evidence status changes in the caller's transaction. The caller
    must commit these changes with the corresponding job completion.
    """
    chain_batch_id = _positive_int(anchor_receipt.get("chain_batch_id"), "chain_batch_id")
    block_number = _positive_int(
        anchor_receipt.get("block_number"), "block_number", allow_zero=True
    )
    chain_id = _positive_int(anchor_receipt.get("chain_id"), "chain_id")
    tx_hash = anchor_receipt.get("transaction_hash")
    if not isinstance(tx_hash, str) or not _TX_RE.fullmatch(tx_hash.lower()):
        raise IntegrityPersistenceError("transaction_hash must be a 0x-prefixed 32-byte hash")
    tx_hash = tx_hash.lower()

    batch = session.scalar(
        select(MerkleBatch)
        .where(MerkleBatch.id == batch_id)
        .with_for_update()
    )
    if batch is None:
        raise IntegrityPersistenceError("Merkle batch does not exist")

    if batch.status == "confirmed":
        stored_chain_batch_id = batch.chain_batch_id
        same_receipt = (
            stored_chain_batch_id is not None
            and int(stored_chain_batch_id) == chain_batch_id
            and batch.tx_hash == tx_hash
            and batch.chain_id == chain_id
            and batch.block_number == block_number
        )
        if same_receipt:
            return batch
        raise IntegrityPersistenceError("confirmed batch cannot be changed")
    if batch.status != "submitted":
        raise IntegrityPersistenceError("only submitted batches can be confirmed")
    if not isinstance(batch.root_hash, str) or not _ROOT_RE.fullmatch(batch.root_hash):
        raise IntegrityPersistenceError("stored batch root is malformed")
    if batch.chain_id != chain_id:
        raise IntegrityPersistenceError("receipt chain ID does not match the submitted batch")
    if batch.tx_hash is None or batch.tx_hash.lower() != tx_hash:
        raise IntegrityPersistenceError("receipt transaction does not match the submitted batch")

    onchain_batch = get_batch(chain_batch_id)
    if (
        str(onchain_batch["root"]).lower() != batch.root_hash
        or int(onchain_batch["leaf_count"]) != batch.leaf_count
    ):
        raise IntegrityPersistenceError("on-chain root or leaf count does not match the batch")
    anchored_at_epoch = int(onchain_batch["anchored_at"])
    if anchored_at_epoch <= 0:
        raise IntegrityPersistenceError("contract returned an invalid anchored_at timestamp")
    anchored_at = datetime.fromtimestamp(anchored_at_epoch, tz=timezone.utc)

    proofs = session.scalars(
        select(MerkleProof)
        .where(MerkleProof.batch_id == batch.id)
        .order_by(MerkleProof.leaf_index)
    ).all()
    if len(proofs) != batch.leaf_count:
        raise IntegrityPersistenceError("submitted batch does not have one proof per leaf")
    if any(proof.leaf_index != index for index, proof in enumerate(proofs)):
        raise IntegrityPersistenceError("proof leaf indexes must be contiguous from zero")

    evidence_ids = [proof.evidence_id for proof in proofs]
    evidence_rows = session.scalars(
        select(Evidence)
        .where(Evidence.id.in_(evidence_ids))
        .order_by(Evidence.uploaded_at, Evidence.id)
        .with_for_update()
    ).all()
    if len(evidence_rows) != batch.leaf_count:
        raise IntegrityPersistenceError("one or more batch evidence records are missing")
    if [evidence.id for evidence in evidence_rows] != evidence_ids:
        raise IntegrityPersistenceError("proof order does not match evidence upload order")

    evidence_by_id = {evidence.id: evidence for evidence in evidence_rows}
    for proof in proofs:
        evidence = evidence_by_id[proof.evidence_id]
        if evidence.status != "stored":
            raise IntegrityPersistenceError("only stored evidence can be marked anchored")
        if not _HASH_RE.fullmatch(evidence.sha256):
            raise IntegrityPersistenceError("stored evidence hash is malformed")
        if leaf_hash(evidence.sha256).hex() != proof.leaf_hash:
            raise IntegrityPersistenceError("proof leaf does not match the stored evidence hash")
        try:
            computed_root = "0x" + root_from_proof(evidence.sha256, proof.proof)
        except (KeyError, TypeError, ValueError):
            raise IntegrityPersistenceError("stored Merkle proof is malformed") from None
        if computed_root != batch.root_hash:
            raise IntegrityPersistenceError("stored Merkle proof does not match the batch root")

    batch.chain_batch_id = chain_batch_id
    batch.tx_hash = tx_hash
    batch.chain_id = chain_id
    batch.block_number = block_number
    batch.anchored_at = anchored_at
    batch.status = "confirmed"
    for evidence in evidence_rows:
        evidence.status = "anchored"

    session.flush()
    return batch


def mark_submitted_batch_failed(
    session: Session,
    *,
    batch_id: UUID,
    failure_code: str = "unspecified",
) -> MerkleBatch:
    """Fail this batch attempt and release its evidence for a later batch.

    Remove unconfirmed proof rows and retain evidence as stored so a new batch
    can safely include it again. The caller owns the database commit.
    """
    allowed_failure_codes = {
        "unspecified",
        "submission_failed",
        "transaction_reverted",
        "wrong_chain_id",
    }
    if failure_code not in allowed_failure_codes:
        raise IntegrityPersistenceError("failure_code is not a supported value")

    batch = session.scalar(
        select(MerkleBatch)
        .where(MerkleBatch.id == batch_id)
        .with_for_update()
    )
    if batch is None:
        raise IntegrityPersistenceError("Merkle batch does not exist")
    if batch.status == "failed":
        return batch
    if batch.status == "confirmed":
        raise IntegrityPersistenceError("a confirmed batch cannot be marked failed")
    if batch.status not in {"building", "submitted"}:
        raise IntegrityPersistenceError("only an unfinished batch can be marked failed")

    linked_evidence = session.scalars(
        select(Evidence)
        .join(MerkleProof, MerkleProof.evidence_id == Evidence.id)
        .where(MerkleProof.batch_id == batch.id)
        .with_for_update()
    ).all()
    if any(evidence.status not in {"stored", "failed"} for evidence in linked_evidence):
        raise IntegrityPersistenceError(
            "failed batch can only release evidence that is still retryable"
        )

    evidence_by_case: dict[UUID, int] = {}
    for evidence in linked_evidence:
        evidence_by_case[evidence.case_id] = evidence_by_case.get(evidence.case_id, 0) + 1
    for case_id in sorted(evidence_by_case, key=str):
        evidence_count = evidence_by_case[case_id]
        append_audit_event(
            session,
            action="anchor_failed",
            target_type="merkle_batch",
            target_id=str(batch.id),
            case_id=case_id,
            details={
                "evidence_count": evidence_count,
                "retryable": True,
                "failure_code": failure_code,
            },
        )

    # A failed evidence marker must not strand an item after its failed batch is
    # released. Never turn an anchored record into a retryable one.
    for evidence in linked_evidence:
        evidence.status = "stored"
    session.execute(delete(MerkleProof).where(MerkleProof.batch_id == batch.id))
    batch.status = "failed"
    session.flush()
    return batch
