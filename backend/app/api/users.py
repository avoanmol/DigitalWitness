"""Admin-only user administration without password or token exposure."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.audit import append_audit_event
from backend.models import User


Role = Literal["reporter", "investigator", "legal", "admin"]


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")


def _json(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id), "email": user.email, "full_name": user.full_name,
        "role": user.role, "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


def create_users_router(*, get_db_dependency: Callable[..., Any], get_current_user_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter(tags=["user administration"])

    @router.get("/admin/users")
    def list_users(db: Session = Depends(get_db_dependency), user: User = Depends(get_current_user_dependency)):
        _require_admin(user)
        rows = db.scalars(select(User).order_by(User.created_at.desc(), User.email)).all()
        return [_json(row) for row in rows]

    @router.patch("/admin/users/{user_id}")
    def update_user(user_id: UUID, payload: UserUpdate, request: Request,
                    db: Session = Depends(get_db_dependency), user: User = Depends(get_current_user_dependency)):
        _require_admin(user)
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(status_code=422, detail="Provide a role or active-state change.")
        target = db.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found.")
        will_be_admin = changes.get("role", target.role) == "admin" and changes.get("is_active", target.is_active)
        if target.id == user.id and not will_be_admin:
            raise HTTPException(status_code=409, detail="You cannot remove your own active administrator access.")
        if target.role == "admin" and target.is_active and not will_be_admin:
            other_admins = db.scalars(
                select(User).where(User.role == "admin", User.is_active.is_(True), User.id != target.id)
            ).first()
            if other_admins is None:
                raise HTTPException(status_code=409, detail="The last active administrator cannot be disabled or demoted.")
        previous = {"role": target.role, "is_active": target.is_active}
        for key, value in changes.items():
            setattr(target, key, value)
        append_audit_event(
            db, action="admin.user.update", target_type="user", actor_id=user.id,
            actor_role=user.role, target_id=str(target.id), ip=request.client.host if request.client else None,
            details={"before": previous, "after": {"role": target.role, "is_active": target.is_active}},
        )
        db.commit()
        db.refresh(target)
        return _json(target)

    return router
