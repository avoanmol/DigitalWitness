"""Case-list and detail APIs shared by the workspace and AI review UI."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.access import can_access_case
from backend.audit import append_audit_event
from backend.models import Analysis, AuditLog, Case, Evidence, MerkleBatch, MerkleProof, ThreatFlag, User, Verification

CaseStatus = Literal["open", "under_review", "closed"]
VerificationStatus = Literal["verified", "altered", "pending", "not_checked", "error"]
Severity = Literal["low", "medium", "high", "critical"]
READ_ROLES = {"reporter", "investigator", "legal", "admin"}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
EXPLORER_TX_URL = {
    137: "https://polygonscan.com/tx/",
    80002: "https://amoy.polygonscan.com/tx/",
    11155111: "https://sepolia.etherscan.io/tx/",
}


def _require_read_access(user: User) -> None:
    if user.role not in READ_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This role cannot read cases.")


def _display_verification(evidence_status: str, result: str | None) -> str:
    if evidence_status == "anchored" and result in {None, "pending"}:
        return "not_checked"
    return result or "pending"


def _serialize_evidence(db: Session, rows: list[Evidence]) -> list[dict[str, Any]]:
    if not rows:
        return []
    evidence_ids = [item.id for item in rows]
    verifications = db.scalars(
        select(Verification)
        .where(Verification.evidence_id.in_(evidence_ids))
        .order_by(Verification.checked_at.desc(), Verification.id.desc())
    ).all()
    latest_verification: dict[UUID, Verification] = {}
    for verification in verifications:
        latest_verification.setdefault(verification.evidence_id, verification)

    proofs = db.scalars(select(MerkleProof).where(MerkleProof.evidence_id.in_(evidence_ids))).all()
    proof_by_evidence = {proof.evidence_id: proof for proof in proofs}
    batch_ids = [proof.batch_id for proof in proofs]
    batches = db.scalars(select(MerkleBatch).where(MerkleBatch.id.in_(batch_ids))).all() if batch_ids else []
    batch_by_id = {batch.id: batch for batch in batches}

    result = []
    for item in rows:
        verification = latest_verification.get(item.id)
        proof = proof_by_evidence.get(item.id)
        batch = batch_by_id.get(proof.batch_id) if proof else None
        chain_id = batch.chain_id if batch else None
        tx_hash = batch.tx_hash if batch else None
        explorer_base = EXPLORER_TX_URL.get(chain_id)
        verification_state = _display_verification(item.status, verification.result if verification else None)
        result.append({
            "id": str(item.id),
            "case_id": str(item.case_id),
            "filename": item.original_filename,
            "mime_type": item.mime_type,
            "size_bytes": item.size_bytes,
            "sha256": item.sha256,
            "status": item.status,
            "analysis_status": item.analysis_status,
            "uploaded_at": item.uploaded_at,
            "verification": verification_state,
            "verification_message": (
                "The batch is confirmed. Run an integrity check to compare the stored file and proof."
                if verification_state == "not_checked" else verification.reason if verification else None
            ),
            "tx_hash": tx_hash,
            "batch_id": str(batch.id) if batch else None,
            "chain_batch_id": str(int(batch.chain_batch_id)) if batch and batch.chain_batch_id is not None else None,
            "batch_root": batch.root_hash if batch else None,
            "chain_id": chain_id,
            "explorer_url": f"{explorer_base}{tx_hash}" if explorer_base and tx_hash else None,
        })
    return result


def _case_summary(case: Case, evidence: list[dict[str, Any]], flags: list[ThreatFlag]) -> dict[str, Any]:
    statuses = [_display_verification(item["status"], item["verification"]) for item in evidence]
    if not evidence:
        verification = None
    elif "altered" in statuses:
        verification = "altered"
    elif "error" in statuses:
        verification = "error"
    elif any(item["status"] != "anchored" for item in evidence):
        verification = "pending"
    elif any(result != "verified" for result in statuses):
        verification = "not_checked"
    else:
        verification = "verified"

    pending_flags = [flag for flag in flags if flag.review_status == "pending"]
    lead = min(
        pending_flags,
        key=lambda item: (SEVERITY_RANK.get(item.severity, 4), str(item.id)),
        default=None,
    )
    return {
        "id": str(case.id),
        "case_ref": case.case_ref,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "created_at": case.created_at,
        "evidence_count": len(evidence),
        "pending_count": sum(item["status"] != "anchored" for item in evidence),
        "threat_count": len(pending_flags),
        "verification": verification,
        "threat_class": lead.threat_class if lead else None,
        "severity": lead.severity if lead else None,
    }


def create_cases_router(
    *,
    get_db_dependency: Callable[..., Any],
    get_current_user_dependency: Callable[..., Any],
) -> APIRouter:
    router = APIRouter()

    @router.get("/cases")
    def list_cases(
        response: Response,
        q: str | None = Query(default=None, max_length=200),
        case_status: CaseStatus | None = Query(default=None, alias="status"),
        verification: VerificationStatus | None = None,
        severity: Severity | None = None,
        threat_class: str | None = Query(default=None, max_length=100),
        from_date: date | None = Query(default=None, alias="from"),
        to_date: date | None = Query(default=None, alias="to"),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        _require_read_access(current_user)
        if from_date and to_date and from_date > to_date:
            raise HTTPException(status_code=422, detail="The from date must be on or before the to date.")

        statement = select(Case).order_by(Case.created_at.desc(), Case.id)
        if current_user.role == "reporter":
            statement = statement.where(Case.created_by == current_user.id)
        if q and q.strip():
            search = f"%{q.strip()}%"
            statement = statement.where(or_(Case.case_ref.ilike(search), Case.title.ilike(search)))
        if case_status:
            statement = statement.where(Case.status == case_status)
        if from_date:
            statement = statement.where(Case.created_at >= datetime.combine(from_date, time.min, tzinfo=timezone.utc))
        if to_date:
            statement = statement.where(Case.created_at < datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=timezone.utc))

        cases = db.scalars(statement).all()
        case_ids = [item.id for item in cases]
        evidence_rows = db.scalars(
            select(Evidence).where(Evidence.case_id.in_(case_ids)).order_by(Evidence.uploaded_at, Evidence.id)
        ).all() if case_ids else []
        serialized_evidence = _serialize_evidence(db, evidence_rows)
        evidence_by_case: dict[UUID, list[dict[str, Any]]] = {case_id: [] for case_id in case_ids}
        evidence_id_to_case = {row.id: row.case_id for row in evidence_rows}
        for item in serialized_evidence:
            evidence_by_case[UUID(item["case_id"])].append(item)

        evidence_ids = [row.id for row in evidence_rows]
        flags = db.scalars(select(ThreatFlag).where(ThreatFlag.evidence_id.in_(evidence_ids))).all() if evidence_ids else []
        flags_by_case: dict[UUID, list[ThreatFlag]] = {case_id: [] for case_id in case_ids}
        for flag in flags:
            case_id = evidence_id_to_case.get(flag.evidence_id)
            if case_id is not None:
                flags_by_case[case_id].append(flag)

        items = [
            _case_summary(case, evidence_by_case.get(case.id, []), flags_by_case.get(case.id, []))
            for case in cases
        ]
        if verification:
            items = [item for item in items if item["verification"] == verification]
        if severity:
            items = [item for item in items if item["severity"] == severity]
        if threat_class:
            expected = threat_class.strip().casefold()
            items = [
                item for item in items
                if item["threat_class"] and item["threat_class"].casefold() == expected
            ]

        total = len(items)
        start = (page - 1) * page_size
        response.headers["Cache-Control"] = "no-store"
        return {"items": items[start : start + page_size], "total": total, "page": page, "page_size": page_size}

    @router.get("/cases/{case_id}")
    def get_case(
        case_id: UUID,
        request: Request,
        response: Response,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        _require_read_access(current_user)
        case = db.get(Case, case_id)
        if case is None or not can_access_case(current_user, case):
            raise HTTPException(status_code=404, detail="Case not found.")

        evidence_rows = db.scalars(
            select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.uploaded_at, Evidence.id)
        ).all()
        evidence = _serialize_evidence(db, evidence_rows)
        evidence_ids = [item.id for item in evidence_rows]
        flags = db.scalars(select(ThreatFlag).where(ThreatFlag.evidence_id.in_(evidence_ids))).all() if evidence_ids else []
        result = _case_summary(case, evidence, flags)
        result["evidence"] = evidence
        append_audit_event(
            db, action="case.evidence_metadata.read", target_type="case",
            actor_id=current_user.id, actor_role=current_user.role,
            target_id=str(case.id), case_id=case.id,
            ip=request.client.host if request.client else None,
            details={"evidence_count": len(evidence)},
        )
        db.commit()
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.get("/cases/{case_id}/activity")
    def get_case_activity(
        case_id: UUID,
        response: Response,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> list[dict[str, Any]]:
        """Return a safe, case-scoped timeline of recorded milestones."""
        _require_read_access(current_user)
        case = db.get(Case, case_id)
        if case is None or not can_access_case(current_user, case):
            raise HTTPException(status_code=404, detail="Case not found.")
        response.headers["Cache-Control"] = "no-store"

        evidence = db.scalars(
            select(Evidence)
            .where(Evidence.case_id == case_id)
            .order_by(Evidence.uploaded_at, Evidence.id)
        ).all()
        evidence_by_id = {str(item.id): item for item in evidence}
        uploader_ids = {item.uploader_id for item in evidence}
        uploaders = db.scalars(select(User).where(User.id.in_(uploader_ids))).all() if uploader_ids else []
        uploader_roles = {str(user.id): user.role for user in uploaders}
        case_owner = db.get(User, case.created_by)
        events: list[dict[str, Any]] = [{
            "id": f"case-created:{case.id}",
            "kind": "case_created",
            "title": "Case created",
            "description": "The case was opened in DigitalWitness.",
            "created_at": case.created_at.isoformat(),
            "actor_role": case_owner.role if case_owner else "reporter",
            "evidence_id": None,
        }]

        # Uploads use the evidence row's server timestamp; the current upload
        # route does not emit a separate audit entry.
        for item in evidence:
            events.append({
                "id": f"evidence-uploaded:{item.id}",
                "kind": "evidence_uploaded",
                "title": "Evidence uploaded",
                "description": item.original_filename,
                "created_at": item.uploaded_at.isoformat(),
                "actor_role": uploader_roles.get(str(item.uploader_id), "reporter"),
                "evidence_id": str(item.id),
            })

        evidence_ids = [item.id for item in evidence]
        analyses = db.scalars(
            select(Analysis).where(Analysis.evidence_id.in_(evidence_ids))
        ).all() if evidence_ids else []
        if current_user.role != "reporter":
            for analysis in analyses:
                if analysis.status not in {"done", "skipped"}:
                    continue
                item = evidence_by_id.get(str(analysis.evidence_id))
                if item is None:
                    continue
                details = analysis.raw_json or {}
                flag_count = details.get("threat_flags")
                entity_count = details.get("entities")
                if isinstance(flag_count, int) and isinstance(entity_count, int):
                    description = f"Automated review completed with {flag_count} potential flags and {entity_count} extracted indicators. Human review is required."
                elif analysis.status == "skipped":
                    description = "Automated review could not extract usable text. This is not an authenticity verdict."
                else:
                    description = "Automated review completed. Human review is required."
                events.append({
                    "id": f"analysis-completed:{analysis.id}",
                    "kind": "analysis_completed",
                    "title": "AI-assisted review completed" if analysis.status == "done" else "AI-assisted review skipped",
                    "description": f"{item.original_filename}: {description}",
                    "created_at": analysis.created_at.isoformat(),
                    "actor_role": "system",
                    "evidence_id": str(item.id),
                })

        # Anchor confirmation has a dedicated database timestamp. It provides
        # an accurate milestone even on installations where the worker has not
        # yet written an audit entry for successful anchoring.
        proof_rows = db.scalars(
            select(MerkleProof).where(MerkleProof.evidence_id.in_(evidence_ids))
        ).all() if evidence_ids else []
        batch_ids = {proof.batch_id for proof in proof_rows}
        batches = db.scalars(
            select(MerkleBatch).where(MerkleBatch.id.in_(batch_ids))
        ).all() if batch_ids else []
        batch_by_id = {batch.id: batch for batch in batches}
        for proof in proof_rows:
            batch = batch_by_id.get(proof.batch_id)
            item = evidence_by_id.get(str(proof.evidence_id))
            if batch is None or item is None or batch.status != "confirmed" or batch.anchored_at is None:
                continue
            events.append({
                "id": f"evidence-anchored:{item.id}:{batch.id}",
                "kind": "evidence_anchored",
                "title": "Evidence anchored",
                "description": f"{item.original_filename} was included in a confirmed on-chain batch.",
                "created_at": batch.anchored_at.isoformat(),
                "actor_role": "system",
                "evidence_id": str(item.id),
            })

        audit_rows = db.scalars(
            select(AuditLog)
            .where(AuditLog.case_id == case_id)
            .order_by(AuditLog.seq.asc())
        ).all()
        action_labels = {
            "anchor_submitted": ("Anchor transaction submitted", "The evidence batch is awaiting chain confirmation."),
            "anchor_failed": ("Anchor attempt failed", "Evidence remains stored and eligible for another anchor attempt."),
            "evidence.verify": ("Integrity check completed", "An integrity check was recorded for this evidence."),
            "analysis_requested": ("AI-assisted review requested", "Automated review was queued. Its output requires human review."),
            "threat_flag_review": ("Potential threat reviewed", "An investigator reviewed a potential threat flag."),
            "case_link_created": ("Related case suggested", "A possible case connection was suggested for review."),
            "case_link_review": ("Case connection reviewed", "An investigator reviewed a proposed case connection."),
            "report_generate": ("Case report generated", "A case report was generated."),
        }
        reporter_actions = {"anchor_submitted", "anchor_failed", "evidence.verify"}
        for row in audit_rows:
            if row.action not in action_labels:
                continue
            if current_user.role == "reporter" and row.action not in reporter_actions:
                continue
            title, description = action_labels[row.action]
            details = row.details or {}
            if row.action == "evidence.verify":
                result_name = details.get("result")
                if result_name in {"verified", "altered", "pending", "error"}:
                    description = f"Integrity check result: {result_name}."
            elif row.action == "threat_flag_review":
                decision = details.get("review_status")
                if decision in {"confirmed", "rejected"}:
                    description = f"An investigator {decision} a potential threat flag."
            elif row.action == "case_link_review":
                decision = details.get("status")
                if decision in {"confirmed", "rejected"}:
                    description = f"An investigator {decision} a proposed case connection."

            evidence_id = row.target_id if row.target_type == "evidence" else None
            target = evidence_by_id.get(evidence_id) if evidence_id else None
            if target is not None and row.action == "evidence.verify":
                description = f"{target.original_filename}: {description}"
            events.append({
                "id": f"audit:{row.id}",
                "kind": row.action,
                "title": title,
                "description": description,
                "created_at": row.created_at.isoformat(),
                "actor_role": row.actor_role or "system",
                "evidence_id": evidence_id,
            })

        events.sort(key=lambda event: event["created_at"], reverse=True)
        return events[:200]

    return router
