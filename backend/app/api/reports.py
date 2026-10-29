"""Role-checked PDF case report endpoint."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.reports.pdf_report import build_case_report
from backend.audit import append_audit_event, verify_audit_chain
from backend.models import (
    Analysis,
    AuditLog,
    Case,
    CaseLink,
    Evidence,
    MerkleBatch,
    MerkleProof,
    ThreatFlag,
    User,
    Verification,
)


REPORT_ROLES = {"investigator", "legal", "admin"}


def create_reports_router(
    *,
    get_db_dependency: Callable[..., Any],
    get_current_user_dependency: Callable[..., Any],
) -> APIRouter:
    router = APIRouter()

    @router.get("/cases/{case_id}/report", response_class=Response)
    def generate_case_report(
        case_id: UUID,
        request: Request,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> Response:
        if current_user.role not in REPORT_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This role cannot generate case reports.")

        case = db.get(Case, case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

        evidence = db.scalars(
            select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.uploaded_at, Evidence.id)
        ).all()
        evidence_ids = [item.id for item in evidence]
        analyses = db.scalars(select(Analysis).where(Analysis.evidence_id.in_(evidence_ids))).all() if evidence_ids else []
        analysis_by_evidence = {item.evidence_id: item for item in analyses}
        proofs = db.scalars(select(MerkleProof).where(MerkleProof.evidence_id.in_(evidence_ids))).all() if evidence_ids else []
        proof_by_evidence = {proof.evidence_id: proof for proof in proofs}
        batch_ids = [proof.batch_id for proof in proofs]
        batches = db.scalars(select(MerkleBatch).where(MerkleBatch.id.in_(batch_ids))).all() if batch_ids else []
        batch_by_id = {batch.id: batch for batch in batches}
        verifications = db.scalars(
            select(Verification).where(Verification.evidence_id.in_(evidence_ids)).order_by(Verification.checked_at.desc())
        ).all() if evidence_ids else []
        latest_verification: dict[UUID, Verification] = {}
        for item in verifications:
            latest_verification.setdefault(item.evidence_id, item)

        evidence_rows: list[dict[str, Any]] = []
        for item in evidence:
            proof = proof_by_evidence.get(item.id)
            batch = batch_by_id.get(proof.batch_id) if proof else None
            evidence_metadata = item.metadata_json or {}
            analysis_data = (analysis_by_evidence[item.id].raw_json or {}) if item.id in analysis_by_evidence else {}
            evidence_rows.append({
                "filename": item.original_filename,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "uploaded_at": item.uploaded_at,
                "tx_hash": batch.tx_hash if batch else None,
                "batch_id": str(batch.id) if batch else None,
                "chain_id": batch.chain_id if batch else None,
                "batch_root": batch.root_hash if batch else None,
                "verification": latest_verification.get(item.id),
                "analysis_status": item.analysis_status,
                "language": analysis_by_evidence[item.id].language if item.id in analysis_by_evidence else None,
                "extraction_method": analysis_data.get("extraction_method"),
                "investigation_categories": analysis_data.get("investigation_categories", evidence_metadata.get("investigation_categories", [])),
                "provenance": analysis_data.get("provenance"),
                "video": analysis_data.get("video"),
            })

        flags = db.scalars(
            select(ThreatFlag).where(ThreatFlag.evidence_id.in_(evidence_ids)).order_by(ThreatFlag.id)
        ).all() if evidence_ids else []
        confirmed_flags = [flag for flag in flags if flag.review_status == "confirmed"]
        unreviewed_flag_count = sum(flag.review_status == "pending" for flag in flags)
        links = db.scalars(
            select(CaseLink).where(or_(CaseLink.case_a_id == case_id, CaseLink.case_b_id == case_id)).order_by(CaseLink.id)
        ).all()
        confirmed_links = [link for link in links if link.status == "confirmed"]
        audit_rows = db.scalars(
            select(AuditLog).where(AuditLog.case_id == case_id).order_by(AuditLog.seq)
        ).all()
        audit_check = verify_audit_chain(db)
        generated_at = datetime.now(timezone.utc)
        pdf_bytes = build_case_report(
            case=case,
            evidence_rows=evidence_rows,
            confirmed_flags=confirmed_flags,
            unreviewed_flag_count=unreviewed_flag_count,
            confirmed_links=confirmed_links,
            case_links=links,
            audit_rows=audit_rows,
            audit_check=audit_check,
            generated_at=generated_at,
        )
        report_hash = hashlib.sha256(pdf_bytes).hexdigest()
        append_audit_event(
            db,
            action="report_generate",
            target_type="case_report",
            actor_id=current_user.id,
            actor_role=current_user.role,
            target_id=str(case_id),
            case_id=case_id,
            ip=request.client.host if request.client else None,
            details={"sha256": report_hash, "format": "application/pdf"},
        )
        db.commit()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{case.case_ref}-report.pdf"',
                "X-Report-SHA256": report_hash,
                "Cache-Control": "no-store",
            },
        )

    return router
