"""Storage-backed verification, with one persisted result and audit event."""
from datetime import datetime, timezone
from hashlib import sha256

from backend.audit import append_audit_event
from backend.models import MerkleBatch, MerkleProof, Verification
from backend.security import decrypt_evidence
from backend.storage import get_encrypted_evidence
from .chain import check_anchor_context, get_chain_id
from .merkle import leaf_hash
from .verify import verify_integrity


def utc(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def batch_fields(batch):
    return {
        "batch_id": str(batch.id) if batch else None,
        "chain_batch_id": str(int(batch.chain_batch_id)) if batch and batch.chain_batch_id is not None else None,
        "tx_hash": batch.tx_hash if batch else None,
        "chain_id": batch.chain_id if batch else None,
    }


def linked_batch(db, evidence_id):
    proof = db.get(MerkleProof, evidence_id)
    return proof, db.get(MerkleBatch, proof.batch_id) if proof else None


def inspect_stored_evidence(evidence, proof, batch):
    result = dict(result="error", expected_hash=evidence.sha256, recomputed_hash=None,
                  computed_root=None, onchain_root=None, reason=None)
    if batch is None or batch.status != "confirmed":
        if evidence.status == "anchored":
            result["reason"] = "The confirmed anchor record is missing or inconsistent."
        else:
            result.update(result="pending", reason="Not anchored yet. Anchoring is queued or awaiting confirmation.")
        return result
    if proof is None or batch.chain_batch_id is None or not batch.tx_hash or batch.block_number is None:
        result["reason"] = "The confirmed anchor record is incomplete."
        return result
    try:
        verifier_chain_id = get_chain_id()
    except Exception:
        result["reason"] = "The configured blockchain network could not be checked."
        return result
    if int(batch.chain_id) != verifier_chain_id:
        result["reason"] = (
            f"This anchor is recorded on chain {batch.chain_id}, but the verifier is "
            f"connected to chain {verifier_chain_id}. The file was not classified as altered."
        )
        return result
    try:
        encrypted = get_encrypted_evidence(evidence.storage_key)
        if len(encrypted) < 28:
            raise ValueError("incomplete encrypted object")
        data = decrypt_evidence(encrypted[12:], encrypted[:12])
        result["recomputed_hash"] = sha256(data).hexdigest()
    except Exception:
        result["reason"] = "Stored evidence could not be read or decrypted. Check storage and encryption configuration."
        return result
    result = verify_integrity(evidence.sha256, result["recomputed_hash"], proof.proof,
                              int(batch.chain_batch_id), batch.root_hash)
    if result["result"] == "verified":
        try:
            valid_leaf = leaf_hash(evidence.sha256).hex() == proof.leaf_hash
            valid_index = 0 <= proof.leaf_index < batch.leaf_count
        except (TypeError, ValueError):
            valid_leaf = valid_index = False
        if not valid_leaf or not valid_index:
            result.update(result="altered", reason="The saved Merkle leaf or index does not match this evidence.")
            return result
        try:
            actual_id = check_anchor_context(batch.tx_hash, batch.root_hash, batch.leaf_count,
                                             batch.chain_id, batch.block_number)
            if actual_id != int(batch.chain_batch_id):
                result.update(result="altered", reason="The saved chain batch ID differs from the anchor transaction.")
        except Exception:
            result.update(result="error", reason="The recorded anchor transaction could not be validated on this chain.")
    return result


def verify_and_record(db, evidence, user, ip=None):
    proof, batch = linked_batch(db, evidence.id)
    result = inspect_stored_evidence(evidence, proof, batch)
    checked_at = datetime.now(timezone.utc)
    verification = Verification(evidence_id=evidence.id, requested_by=user.id,
                                checked_at=checked_at, **result)
    db.add(verification)
    db.flush()
    append_audit_event(db, action="evidence.verify", target_type="evidence",
                       target_id=str(evidence.id), case_id=evidence.case_id,
                       actor_id=user.id, actor_role=user.role, ip=ip,
                       details={"verification_id": str(verification.id), **result, **batch_fields(batch)})
    message = {
        "verified": f"Unchanged since anchoring on {utc(batch.anchored_at) if batch else ''}. This does not prove the file was genuine before upload.",
        "altered": "This file no longer matches what was recorded and anchored. Do not rely on it.",
        "pending": "Not anchored yet. The file is stored and hashed; anchoring is queued.",
        "error": "Verification could not be completed. This is not a finding about the file.",
    }[result["result"]]
    response = {"evidence_id": str(evidence.id), "verification_id": str(verification.id),
                **result, **batch_fields(batch), "message": message, "checked_at": utc(checked_at)}
    db.commit()
    return response
