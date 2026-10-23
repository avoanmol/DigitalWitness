
import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditLog


GENESIS_HASH = "0" * 64


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
    """Append an audit event linked to the previous event's hash."""

    previous = db.scalar(
        select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)
    )
    prev_hash = previous.entry_hash if previous else GENESIS_HASH

    payload = {
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "actor_id": str(actor_id) if actor_id else None,
        "actor_role": actor_role,
        "case_id": str(case_id) if case_id else None,
        "ip": ip,
        "details": details or {},
        "prev_hash": prev_hash,
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    entry_hash = hashlib.sha256(canonical).hexdigest()

    event = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        case_id=case_id,
        ip=ip,
        details=details or {},
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )

    db.add(event)
    db.flush()
    return event

def verify_audit_chain(db: Session) -> dict[str, Any]:
    """Verify audit entry hashes and links between consecutive entries."""
    entries = db.scalars(
        select(AuditLog).order_by(AuditLog.seq.asc())
    ).all()

    expected_prev_hash = GENESIS_HASH

    for entry in entries:
        if entry.prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "entries_checked": 0,
                "failed_entry_id": str(entry.id),
                "reason": "Previous hash does not match the preceding entry.",
            }

        payload = {
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

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

        calculated_hash = hashlib.sha256(canonical).hexdigest()

        if calculated_hash != entry.entry_hash:
            return {
                "valid": False,
                "entries_checked": 0,
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
