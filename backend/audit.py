"""Append-only, hash-linked audit events.

New entries cover their sequence number and timestamp in the hash. The verifier
also accepts the original pre-sequence format so existing local audit history
remains verifiable after upgrade.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.models import AuditLog


GENESIS_HASH = "0" * 64
AUDIT_CHAIN_LOCK_KEY = 0x41554449  # ASCII "AUDI"; shared by every app worker.


def _timestamp(value: datetime) -> str:
    """Use a stable UTC representation for hashes and API output."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _legacy_payload(entry: AuditLog) -> dict[str, Any]:
    """Reproduce the original hash format for already-written events."""
    return {
        "action": entry.action,
        "target_type": entry.target_type,
        "target_id": entry.target_id,
        "actor_id": str(entry.actor_id) if entry.actor_id else None,
        "actor_role": entry.actor_role,
        "case_id": str(entry.case_id) if entry.case_id else None,
        "ip": entry.ip,
        "details": entry.details or {},
        "prev_hash": entry.prev_hash,
    }


def _current_payload(entry: AuditLog) -> dict[str, Any]:
    return {
        **_legacy_payload(entry),
        "seq": entry.seq,
        "created_at": _timestamp(entry.created_at),
    }


def append_audit_event(
    db: Session,
    *,
    action: str,
    target_type: str,
    actor_id: UUID | None = None,
    actor_role: str | None = None,
    target_id: str | None = None,
    case_id: UUID | None = None,
    ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Append one hash-linked event in the caller's transaction."""
    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": AUDIT_CHAIN_LOCK_KEY},
    )
    previous = db.scalar(select(AuditLog).order_by(AuditLog.seq.desc()).limit(1))
    prev_hash = previous.entry_hash if previous else GENESIS_HASH

    # Reserve the PostgreSQL identity value while holding the chain lock so
    # concurrent API/worker processes cannot hash an out-of-order sequence.
    seq = db.scalar(text("SELECT nextval(pg_get_serial_sequence('audit_log', 'seq'))"))
    if seq is None:
        raise RuntimeError("Could not reserve an audit sequence number.")
    created_at = datetime.now(timezone.utc)
    event = AuditLog(
        seq=int(seq),
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        case_id=case_id,
        ip=ip,
        details=details or {},
        prev_hash=prev_hash,
        entry_hash="0" * 64,
        created_at=created_at,
    )
    event.entry_hash = _canonical_hash(_current_payload(event))
    db.add(event)
    db.flush()
    return event


def verify_audit_chain(db: Session) -> dict[str, Any]:
    """Verify hashes and links, including legacy entries written before v2."""
    entries = db.scalars(select(AuditLog).order_by(AuditLog.seq.asc())).all()
    expected_prev_hash = GENESIS_HASH

    for checked, entry in enumerate(entries, start=1):
        if entry.prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "entries_checked": checked - 1,
                "failed_entry_id": str(entry.id),
                "reason": "Previous hash does not match the preceding entry.",
            }

        calculated_hash = _canonical_hash(_current_payload(entry))
        # Compatibility for old data; all new events use the current payload.
        if calculated_hash != entry.entry_hash:
            calculated_hash = _canonical_hash(_legacy_payload(entry))
        if calculated_hash != entry.entry_hash:
            return {
                "valid": False,
                "entries_checked": checked - 1,
                "failed_entry_id": str(entry.id),
                "reason": "Entry hash does not match its contents.",
            }
        expected_prev_hash = entry.entry_hash

    return {
        "valid": True,
        "entries_checked": len(entries),
        "failed_entry_id": None,
        "reason": None,
    }
