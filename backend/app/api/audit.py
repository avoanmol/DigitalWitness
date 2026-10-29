"""Role-protected audit history and integrity-check routes."""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.audit import append_audit_event, verify_audit_chain
from backend.models import AuditLog, User


AUDIT_ROLES = {"legal", "admin"}


def _require_audit_role(user: User) -> None:
    if user.role not in AUDIT_ROLES:
        raise HTTPException(status_code=403, detail="Audit access is limited to legal and admin roles.")


def _serialize(entry: AuditLog) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "seq": entry.seq,
        "actor_role": entry.actor_role,
        "action": entry.action,
        "target_type": entry.target_type,
        "target_id": entry.target_id,
        "case_id": str(entry.case_id) if entry.case_id else None,
        "details": entry.details or {},
        "prev_hash": entry.prev_hash,
        "entry_hash": entry.entry_hash,
        "created_at": entry.created_at.isoformat(),
    }


def create_audit_router(
    *,
    get_db_dependency: Callable[..., Any],
    get_current_user_dependency: Callable[..., Any],
) -> APIRouter:
    router = APIRouter(tags=["audit"])

    @router.get("/audit")
    def list_audit_events(
        case_id: UUID | None = None,
        limit: int = Query(default=200, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        db: Session = Depends(get_db_dependency),
        user: User = Depends(get_current_user_dependency),
    ) -> list[dict[str, Any]]:
        _require_audit_role(user)
        query = select(AuditLog)
        if case_id is not None:
            query = query.where(AuditLog.case_id == case_id)
        rows = db.scalars(
            query.order_by(AuditLog.seq.desc()).offset(offset).limit(limit)
        ).all()
        return [_serialize(row) for row in rows]

    @router.get("/audit/verify")
    def verify_audit_events(
        request: Request,
        db: Session = Depends(get_db_dependency),
        user: User = Depends(get_current_user_dependency),
    ) -> dict[str, Any]:
        _require_audit_role(user)
        result = verify_audit_chain(db)
        latest = db.scalar(select(AuditLog).order_by(AuditLog.seq.desc()).limit(1))
        result["verified_through_seq"] = latest.seq if latest else 0
        append_audit_event(
            db,
            action="audit.chain.verify",
            target_type="audit_log",
            actor_id=user.id,
            actor_role=user.role,
            ip=request.client.host if request.client else None,
            details={"valid": result["valid"], "entries_checked": result["entries_checked"]},
        )
        db.commit()
        return result

    return router
