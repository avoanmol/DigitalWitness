from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.integrity.batcher import (
    DEFAULT_ANCHOR_BATCH_SIZE,
    anchor_persisted_evidence_records,
    retry_delay_after_failure,
    should_trigger_batch,
)
from backend.app.integrity.chain import TransactionReverted, get_chain_id, wait_for_anchor
from backend.app.integrity.persistence import (
    confirm_submitted_batch,
    mark_submitted_batch_failed,
)
from backend.database import SessionLocal, engine
from backend.models import Evidence, MerkleBatch, MerkleProof

logger = logging.getLogger("digitalwitness.integrity_worker")
_ADVISORY_LOCK_ID = 0x4457494E54454752


def _configured_batch_size() -> int:
    try:
        value = int(os.environ.get("ANCHOR_BATCH_SIZE", DEFAULT_ANCHOR_BATCH_SIZE))
    except ValueError as exc:
        raise RuntimeError("ANCHOR_BATCH_SIZE must be an integer") from exc
    if not 1 <= value <= 0xFFFFFFFF:
        raise RuntimeError("ANCHOR_BATCH_SIZE must be between 1 and 4294967295")
    return value


def _poll_seconds() -> float:
    try:
        seconds = float(os.environ.get("ANCHOR_WORKER_POLL_SECONDS", "5"))
    except ValueError as exc:
        raise RuntimeError("ANCHOR_WORKER_POLL_SECONDS must be numeric") from exc
    if seconds <= 0:
        raise RuntimeError("ANCHOR_WORKER_POLL_SECONDS must be positive")
    return seconds


def _load_candidates(session: Session) -> list[dict[str, Any]]:
    """Read the oldest stored evidence that has no persisted proof yet."""
    already_in_batch = (
        select(MerkleProof.evidence_id)
        .where(MerkleProof.evidence_id == Evidence.id)
        .exists()
    )
    rows = session.execute(
        select(Evidence.id, Evidence.uploaded_at, Evidence.status, Evidence.sha256)
        .where(Evidence.status == "stored", ~already_in_batch)
        .order_by(Evidence.uploaded_at, Evidence.id)
        .limit(_configured_batch_size())
    ).mappings().all()
    return [dict(row) for row in rows]


def run_once(
    *,
    session_factory=SessionLocal,
    now: datetime | None = None,
) -> bool:
    """Anchor one eligible batch; return whether a batch was processed."""
    _recover_abandoned_batches(session_factory)

    with session_factory() as session:
        candidates = _load_candidates(session)

    current_time = now or datetime.now(timezone.utc)
    if not should_trigger_batch(candidates, current_time):
        return False

    logger.info("Starting anchor batch with %s stored evidence records", len(candidates))
    result = anchor_persisted_evidence_records(candidates, session_factory)
    logger.info(
        "Confirmed Merkle batch %s with %s evidence records; tx=%s root=%s",
        result["batch_id"],
        result["leaf_count"],
        result["transaction_hash"],
        result["root"],
    )
    return True


def _require_chain_configuration() -> None:
    contract = os.environ.get("CHAIN_CONTRACT_ADDRESS", "")
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", contract):
        raise RuntimeError("Set CHAIN_CONTRACT_ADDRESS to the deployed 20-byte address")

    sender = os.environ.get("CHAIN_SENDER_ADDRESS", "")
    private_key = os.environ.get("CHAIN_PRIVATE_KEY", "")
    if sender and not re.fullmatch(r"0x[0-9a-fA-F]{40}", sender):
        raise RuntimeError("CHAIN_SENDER_ADDRESS must be a 20-byte hexadecimal address")
    if private_key and not re.fullmatch(r"0x[0-9a-fA-F]{64}", private_key):
        raise RuntimeError("CHAIN_PRIVATE_KEY must be a 32-byte hexadecimal key")
    if not sender and not private_key:
        raise RuntimeError(
            "Set CHAIN_SENDER_ADDRESS for an unlocked node or CHAIN_PRIVATE_KEY for signing"
        )
    # Fail at startup instead of allowing the worker to submit to a local
    # Hardhat RPC when the Amoy demo is configured (Amoy is the default guard).
    get_chain_id()


def _recover_abandoned_batches(session_factory=SessionLocal) -> None:
    """Retain ambiguous builders and resume transactions without rebroadcasting."""
    try:
        timeout = int(os.environ.get("ANCHOR_BUILDING_TIMEOUT_SECONDS", "300"))
    except ValueError as exc:
        raise RuntimeError("ANCHOR_BUILDING_TIMEOUT_SECONDS must be an integer") from exc
    if timeout < 1:
        raise RuntimeError("ANCHOR_BUILDING_TIMEOUT_SECONDS must be positive")

    cutoff = datetime.now(timezone.utc).timestamp() - timeout
    cutoff_at = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    with session_factory() as session:
        stale_ids = session.scalars(
            select(MerkleBatch.id).where(
                MerkleBatch.status == "building",
                MerkleBatch.created_at < cutoff_at,
            )
        ).all()
        for batch_id in stale_ids:
            logger.debug("Stale building batch %s is retained for reconciliation", batch_id)

    with session_factory() as session:
        pending = session.execute(
            select(
                MerkleBatch.id,
                MerkleBatch.root_hash,
                MerkleBatch.leaf_count,
                MerkleBatch.tx_hash,
                MerkleBatch.chain_id,
            ).where(MerkleBatch.status == "submitted")
        ).all()

    for batch_id, root, leaf_count, tx_hash, chain_id in pending:
        try:
            receipt = wait_for_anchor(
                {"transaction_hash": tx_hash, "chain_id": int(chain_id)},
                root,
                int(leaf_count),
            )
            with session_factory() as session:
                confirm_submitted_batch(
                    session, batch_id=batch_id, anchor_receipt=receipt
                )
                session.commit()
            logger.info("Recovered submitted Merkle batch %s", batch_id)
        except TransactionReverted:
            logger.warning("Confirmed reverted transaction for batch %s", batch_id)
            with session_factory() as session:
                mark_submitted_batch_failed(
                    session,
                    batch_id=batch_id,
                    failure_code="transaction_reverted",
                )
                session.commit()
        except Exception:
            logger.warning("Submitted batch %s retained; confirmation unavailable", batch_id)


def run_forever() -> None:
    """Run the polling worker under a PostgreSQL advisory singleton lock."""
    _require_chain_configuration()
    poll_seconds = _poll_seconds()
    _configured_batch_size()
    failures = 0

    with engine.connect() as lock_connection:
        acquired = bool(
            lock_connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": _ADVISORY_LOCK_ID},
            ).scalar_one()
        )
        lock_connection.commit()
        if not acquired:
            raise RuntimeError("another integrity worker already holds the worker lock")

        logger.info("Integrity worker started; polling every %.1f seconds", poll_seconds)
        try:
            while True:
                try:
                    processed = run_once()
                except Exception:
                    failures += 1
                    retry_delay = retry_delay_after_failure(failures)
                    if retry_delay is None:
                        # Keep evidence retryable while avoiding a tight failure loop.
                        retry_delay = max(60.0, poll_seconds)
                        failures = 0
                    logger.exception(
                        "Integrity batch attempt failed; retrying in %.1f seconds",
                        retry_delay,
                    )
                    time.sleep(retry_delay)
                    continue

                failures = 0
                time.sleep(0.5 if processed else poll_seconds)
        finally:
            lock_connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": _ADVISORY_LOCK_ID},
            )
            lock_connection.commit()


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run_forever()


if __name__ == "__main__":
    main()
