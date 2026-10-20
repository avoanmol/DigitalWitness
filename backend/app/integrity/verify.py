from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict

from .chain import get_batch
from .merkle import ProofStep, root_from_proof


VerificationStatus = Literal["verified", "altered", "pending", "error"]


class VerificationResult(TypedDict):
    result: VerificationStatus
    expected_hash: str | None
    recomputed_hash: str | None
    computed_root: str | None
    onchain_root: str | None
    reason: str | None


def verify_integrity(
    expected_hash: str | None,
    recomputed_hash: str | None,
    proof: Sequence[ProofStep] | None,
    chain_batch_id: int | None,
    stored_batch_root: str | None = None,
) -> VerificationResult:
    """Verify re-hashed file bytes, the stored proof, and the chain root."""
    if proof is None or chain_batch_id is None:
        return {
            "result": "pending",
            "expected_hash": expected_hash,
            "recomputed_hash": recomputed_hash,
            "computed_root": None,
            "onchain_root": None,
            "reason": "Evidence has not been anchored yet.",
        }

    if expected_hash is None or recomputed_hash is None:
        return {
            "result": "error",
            "expected_hash": expected_hash,
            "recomputed_hash": recomputed_hash,
            "computed_root": None,
            "onchain_root": None,
            "reason": "Evidence bytes or the recorded hash could not be read.",
        }

    if expected_hash != recomputed_hash:
        return {
            "result": "altered",
            "expected_hash": expected_hash,
            "recomputed_hash": recomputed_hash,
            "computed_root": None,
            "onchain_root": None,
            "reason": "The file differs from the hash recorded at upload.",
        }

    try:
        computed_root = "0x" + root_from_proof(recomputed_hash, proof)
    except (ValueError, KeyError, TypeError):
        return {
            "result": "altered",
            "expected_hash": expected_hash,
            "recomputed_hash": recomputed_hash,
            "computed_root": None,
            "onchain_root": None,
            "reason": "The stored Merkle proof is invalid.",
        }

    if stored_batch_root is not None:
        normalized_stored_root = stored_batch_root.lower()
        if not normalized_stored_root.startswith("0x"):
            normalized_stored_root = "0x" + normalized_stored_root
        if computed_root != normalized_stored_root:
            return {
                "result": "altered",
                "expected_hash": expected_hash,
                "recomputed_hash": recomputed_hash,
                "computed_root": computed_root,
                "onchain_root": None,
                "reason": "The proof does not match the stored batch root.",
            }

    try:
        batch = get_batch(chain_batch_id)
    except Exception:
        return {
            "result": "error",
            "expected_hash": expected_hash,
            "recomputed_hash": recomputed_hash,
            "computed_root": computed_root,
            "onchain_root": None,
            "reason": "The chain could not be reached or the batch could not be read.",
        }

    onchain_root = str(batch["root"]).lower()
    if computed_root != onchain_root:
        return {
            "result": "altered",
            "expected_hash": expected_hash,
            "recomputed_hash": recomputed_hash,
            "computed_root": computed_root,
            "onchain_root": onchain_root,
            "reason": "The computed root does not match the on-chain root.",
        }

    return {
        "result": "verified",
        "expected_hash": expected_hash,
        "recomputed_hash": recomputed_hash,
        "computed_root": computed_root,
        "onchain_root": onchain_root,
        "reason": None,
    }


def verify_evidence(
    file_sha256_hex: str,
    proof: Sequence[ProofStep],
    batch_id: int,
) -> bool:
    """Compatibility helper for a hash/proof pair that is already re-computed."""
    return (
        verify_integrity(
            expected_hash=file_sha256_hex,
            recomputed_hash=file_sha256_hex,
            proof=proof,
            chain_batch_id=batch_id,
        )["result"]
        == "verified"
    )

