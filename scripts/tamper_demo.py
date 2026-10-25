from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.integrity.batcher import anchor_evidence_records  # noqa: E402
from app.integrity.chain import ChainError, get_batch  # noqa: E402
from app.integrity.verify import verify_integrity  # noqa: E402


TAMPER_SUFFIX = b"\nDigitalWitness tamper demo mutation"


def sha256_file(path: Path, append: bytes = b"") -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    digest.update(append)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Anchor selected files in a local Hardhat batch, verify them, "
            "and demonstrate detection of an in-memory tamper."
        )
    )
    parser.add_argument("files", nargs="+", type=Path, help="file(s) to hash and anchor")
    args = parser.parse_args()

    for path in args.files:
        if not path.is_file():
            parser.error(f"not a file: {path}")

    if not os.environ.get("CHAIN_CONTRACT_ADDRESS"):
        parser.error("set CHAIN_CONTRACT_ADDRESS to the deployed EvidenceAnchor address")
    if not os.environ.get("CHAIN_SENDER_ADDRESS"):
        parser.error("set CHAIN_SENDER_ADDRESS to an unlocked local Hardhat account")

    hash_started = time.perf_counter()
    uploaded_at = datetime.now(timezone.utc).isoformat()
    records = [
        {
            "id": str(uuid4()),
            "sha256": sha256_file(path),
            "status": "stored",
            "uploaded_at": uploaded_at,
        }
        for path in args.files
    ]
    hash_elapsed = time.perf_counter() - hash_started

    try:
        anchor_started = time.perf_counter()
        batch = anchor_evidence_records(records)
        anchor_elapsed = time.perf_counter() - anchor_started
        onchain_batch = get_batch(batch["chain_batch_id"])
    except (ChainError, OSError, ValueError) as exc:
        print(f"Demo failed: {exc}", file=sys.stderr)
        return 1

    proofs = {proof["evidence_id"]: proof for proof in batch["evidence_proofs"]}
    print(f"Anchored chain batch: {batch['chain_batch_id']}")
    print(f"Root: {batch['root']}")
    print(f"Leaves: {batch['leaf_count']}")
    print(f"Transaction: {batch['transaction_hash']}")

    all_expected_results = True
    for path, record in zip(args.files, records, strict=True):
        proof = proofs[record["id"]]
        verify_started = time.perf_counter()
        current_hash = sha256_file(path)
        verified = verify_integrity(
            expected_hash=record["sha256"],
            recomputed_hash=current_hash,
            proof=proof["siblings"],
            chain_batch_id=batch["chain_batch_id"],
            stored_batch_root=onchain_batch["root"],
        )
        verify_elapsed = time.perf_counter() - verify_started

        tamper_started = time.perf_counter()
        altered_hash = sha256_file(path, append=TAMPER_SUFFIX)
        tampered = verify_integrity(
            expected_hash=record["sha256"],
            recomputed_hash=altered_hash,
            proof=proof["siblings"],
            chain_batch_id=batch["chain_batch_id"],
            stored_batch_root=onchain_batch["root"],
        )
        tamper_elapsed = time.perf_counter() - tamper_started

        print(f"{path}: original={verified['result']}, tampered-copy={tampered['result']}")
        print(
            f"  hash={hash_elapsed:.3f}s, anchor={anchor_elapsed:.3f}s, "
            f"verify={verify_elapsed:.3f}s, tamper-check={tamper_elapsed:.3f}s"
        )
        all_expected_results &= (
            verified["result"] == "verified" and tampered["result"] == "altered"
        )

    if not all_expected_results:
        print("Unexpected verification result; inspect RPC and local node configuration.", file=sys.stderr)
        return 1

    print("Tamper demo passed. Source files were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
