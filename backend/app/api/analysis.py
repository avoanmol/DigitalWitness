"""Authenticated AI analysis and human-reviewed case-link endpoints."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from backend.access import can_access_case
from backend.app.ai.jobs import enqueue_analysis
from backend.app.ai.schemas import FlagReviewRequest, LinkCreateRequest, LinkReviewRequest
from backend.audit import append_audit_event
from backend.models import Analysis, Case, CaseLink, Entity, Evidence, ThreatFlag, User

READ_ROLES = {"investigator", "legal", "admin"}
REVIEW_ROLES = {"investigator", "admin"}


def _require_role(user: User, roles: set[str]) -> None:
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="This role cannot access AI analysis or case links.")


def _require_case_access(user: User, db: Session, case_id: UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None or not can_access_case(user, case):
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


def _flag_json(flag: ThreatFlag, feedback: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": str(flag.id), "evidence_id": str(flag.evidence_id),
        "threat_class": flag.threat_class, "severity": flag.severity,
        "snippet": flag.snippet, "confidence": flag.confidence,
        "reason": flag.reason, "review_status": flag.review_status,
        "reviewed_by": str(flag.reviewed_by) if flag.reviewed_by else None,
        "reviewed_at": flag.reviewed_at.isoformat() if flag.reviewed_at else None,
        "review_reason": (feedback or {}).get("reason"),
    }


def _analysis_json(db: Session, evidence: Evidence, analysis: Analysis | None) -> dict[str, Any]:
    entities = db.scalars(select(Entity).where(Entity.evidence_id == evidence.id).order_by(Entity.type, Entity.normalised_value)).all()
    flags = db.scalars(select(ThreatFlag).where(ThreatFlag.evidence_id == evidence.id).order_by(ThreatFlag.id)).all()
    analysis_json = analysis.raw_json or {} if analysis else {}
    review_feedback = analysis_json.get("review_feedback", {})
    return {
        "evidence_id": str(evidence.id), "status": analysis.status if analysis else evidence.analysis_status,
        "language": analysis.language if analysis else None, "text": analysis.text if analysis else None,
        "model": analysis.model if analysis else None, "prompt_version": analysis.prompt_version if analysis else None,
        "analysis_source": analysis_json.get("source"),
        "human_review_required": True,
        "investigation_categories": analysis_json.get("investigation_categories", (evidence.metadata_json or {}).get("investigation_categories", [])),
        "extraction_method": analysis_json.get("extraction_method"),
        "provenance": analysis_json.get("provenance"),
        "coverage": analysis_json.get("coverage"),
        "video": analysis_json.get("video"),
        "entities": [{
            "id": str(item.id), "type": item.type, "raw": item.raw_value,
            "normalised": item.normalised_value, "confidence": item.confidence,
            "source_span": item.source_span,
        } for item in entities],
        "flags": [_flag_json(item, review_feedback.get(str(item.id))) for item in flags],
    }


def _link_json(link: CaseLink, other: Case | None = None) -> dict[str, Any]:
    return {
        "id": str(link.id), "case_a_id": str(link.case_a_id), "case_b_id": str(link.case_b_id),
        "other_case_ref": other.case_ref if other else None,
        "other_case_title": other.title if other else None,
        "shared_entities": link.shared_entities or [], "confidence": link.confidence,
        "status": link.status, "created_by": link.created_by,
        "reviewed_by": str(link.reviewed_by) if link.reviewed_by else None,
        "review_reason": link.review_reason,
    }


def create_analysis_router(*, get_db_dependency: Callable[..., Any], get_current_user_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter()

    @router.get("/ai/review-insights")
    def get_review_insights(
        request: Request,
        response: Response,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        """Aggregate reviewer feedback without returning evidence or case data."""
        _require_role(current_user, READ_ROLES)
        response.headers["Cache-Control"] = "no-store"

        reviewed_rows = db.execute(
            select(ThreatFlag, Evidence, Analysis)
            .join(Evidence, Evidence.id == ThreatFlag.evidence_id)
            .outerjoin(Analysis, Analysis.evidence_id == Evidence.id)
            .where(ThreatFlag.review_status.in_(("confirmed", "rejected")))
            .order_by(ThreatFlag.id)
        ).all()

        reason_values = {
            "source_supports_flag", "reported_or_quoted_context",
            "educational_or_hypothetical_context", "wrong_category",
            "snippet_not_supported", "extraction_unclear", "duplicate_or_repeated",
            "insufficient_context", "other",
        }
        dimensions: dict[str, dict[str, dict[str, int]]] = {
            name: {} for name in ("category", "language", "media_type", "review_reason")
        }
        outcomes = {"confirmed": 0, "rejected": 0}

        def media_kind(mime_type: str | None) -> str:
            value = (mime_type or "").casefold()
            if value.startswith("image/"):
                return "image"
            if value == "application/pdf":
                return "pdf"
            if value.startswith("video/"):
                return "video"
            if value.startswith("audio/"):
                return "audio"
            if value.startswith("text/"):
                return "text"
            return "other"

        def add(dimension: str, label: str, outcome: str) -> None:
            counts = dimensions[dimension].setdefault(label, {"confirmed": 0, "rejected": 0})
            counts[outcome] += 1

        for flag, evidence, analysis in reviewed_rows:
            outcome = flag.review_status
            outcomes[outcome] += 1
            category = (flag.threat_class or "unknown").strip().casefold() or "unknown"
            language = (analysis.language or "unknown").strip().casefold() if analysis else "unknown"
            raw = analysis.raw_json or {} if analysis else {}
            feedback = raw.get("review_feedback", {})
            item_feedback = feedback.get(str(flag.id), {}) if isinstance(feedback, dict) else {}
            reason = item_feedback.get("reason") if isinstance(item_feedback, dict) else None
            reason = reason if reason in reason_values else "not_recorded"
            add("category", category, outcome)
            add("language", language or "unknown", outcome)
            add("media_type", media_kind(evidence.mime_type), outcome)
            add("review_reason", reason, outcome)

        def buckets(name: str) -> list[dict[str, Any]]:
            return [
                {"label": label, **counts, "total": counts["confirmed"] + counts["rejected"]}
                for label, counts in sorted(dimensions[name].items())
            ]

        append_audit_event(
            db, action="ai_review_insights_read", target_type="ai_review_feedback",
            actor_id=current_user.id, actor_role=current_user.role,
            ip=request.client.host if request.client else None,
            details={"reviewed_flag_count": len(reviewed_rows)},
        )
        db.commit()
        return {
            "source": "human_review_feedback",
            "reviewed_flag_count": len(reviewed_rows),
            "outcomes": outcomes,
            "by_category": buckets("category"),
            "by_language": buckets("language"),
            "by_media_type": buckets("media_type"),
            "by_review_reason": buckets("review_reason"),
            "training_enabled": False,
            "limitations": [
                "These are counts for AI flags that a reviewer confirmed or rejected; they are not accuracy, precision, recall, or false-positive rates.",
                "Evidence without a generated flag is excluded, so missed threats cannot be counted here.",
                "Reviews may not be independently adjudicated and should not be treated as representative of all cases.",
                "This feedback is not used to train or update the analysis model.",
            ],
        }

    @router.get("/evidence/{evidence_id}/analysis")
    def get_evidence_analysis(evidence_id: UUID, response: Response,
        current_user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db_dependency)):
        _require_role(current_user, READ_ROLES)
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found.")
        _require_case_access(current_user, db, evidence.case_id)
        response.headers["Cache-Control"] = "no-store"
        analysis = db.scalar(select(Analysis).where(Analysis.evidence_id == evidence_id))
        return _analysis_json(db, evidence, analysis)

    @router.get("/cases/{case_id}/investigative-summary")
    def get_case_investigative_summary(
        case_id: UUID,
        request: Request,
        response: Response,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        """Return a source-linked, deterministic rollup; no generative conclusions."""
        _require_role(current_user, READ_ROLES)
        case = _require_case_access(current_user, db, case_id)
        evidence_rows = db.scalars(
            select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.uploaded_at, Evidence.id)
        ).all()
        evidence_ids = [item.id for item in evidence_rows]
        analyses = db.scalars(select(Analysis).where(Analysis.evidence_id.in_(evidence_ids))).all() if evidence_ids else []
        analysis_by_evidence = {item.evidence_id: item for item in analyses}
        flags = db.scalars(
            select(ThreatFlag).where(ThreatFlag.evidence_id.in_(evidence_ids)).order_by(ThreatFlag.evidence_id, ThreatFlag.id)
        ).all() if evidence_ids else []
        flags_by_evidence: dict[UUID, list[ThreatFlag]] = {item.id: [] for item in evidence_rows}
        for flag in flags:
            flags_by_evidence.setdefault(flag.evidence_id, []).append(flag)

        category_items: dict[str, dict[str, Any]] = {}
        evidence_summary: list[dict[str, Any]] = []
        feedback_by_flag: dict[str, dict[str, Any]] = {}
        completed = 0
        for evidence in evidence_rows:
            analysis = analysis_by_evidence.get(evidence.id)
            raw = analysis.raw_json or {} if analysis else {}
            if analysis and analysis.status == "done":
                completed += 1
            categories = raw.get("investigation_categories") or (evidence.metadata_json or {}).get("investigation_categories", [])
            flags_for_evidence = flags_by_evidence.get(evidence.id, [])
            for flag in flags_for_evidence:
                category = flag.threat_class
                rollup = category_items.setdefault(category, {
                    "category": category, "evidence_ids": [], "flag_count": 0,
                    "focus_evidence_ids": [], "flag_evidence_ids": [],
                    "pending_count": 0, "confirmed_count": 0, "rejected_count": 0,
                })
                if str(evidence.id) not in rollup["evidence_ids"]:
                    rollup["evidence_ids"].append(str(evidence.id))
                if str(evidence.id) not in rollup["flag_evidence_ids"]:
                    rollup["flag_evidence_ids"].append(str(evidence.id))
                rollup["flag_count"] += 1
                rollup[f"{flag.review_status}_count"] = rollup.get(f"{flag.review_status}_count", 0) + 1
                feedback = raw.get("review_feedback", {}).get(str(flag.id))
                if feedback:
                    feedback_by_flag[str(flag.id)] = feedback
            for category in categories:
                rollup = category_items.setdefault(category, {
                    "category": category, "evidence_ids": [], "flag_count": 0,
                    "focus_evidence_ids": [], "flag_evidence_ids": [],
                    "pending_count": 0, "confirmed_count": 0, "rejected_count": 0,
                })
                if str(evidence.id) not in rollup["evidence_ids"]:
                    rollup["evidence_ids"].append(str(evidence.id))
                if str(evidence.id) not in rollup["focus_evidence_ids"]:
                    rollup["focus_evidence_ids"].append(str(evidence.id))
            evidence_summary.append({
                "evidence_id": str(evidence.id),
                "filename": evidence.original_filename,
                "uploaded_at": evidence.uploaded_at.isoformat(),
                "analysis_status": analysis.status if analysis else evidence.analysis_status,
                "language": analysis.language if analysis else None,
                "extraction_method": raw.get("extraction_method"),
                "coverage": raw.get("coverage"),
                "focus_categories": categories,
                "flags": [{
                    "id": str(flag.id), "category": flag.threat_class,
                    "severity": flag.severity, "snippet": flag.snippet,
                    "review_status": flag.review_status,
                    "review_reason": (feedback_by_flag.get(str(flag.id)) or {}).get("reason"),
                } for flag in flags_for_evidence],
            })

        pending_flags = sum(flag.review_status == "pending" for flag in flags)
        not_completed = len(evidence_rows) - completed
        overview = (
            f"{len(evidence_rows)} evidence item(s) are attached; {completed} have completed analysis, "
            f"{not_completed} are pending, failed, or skipped, and {pending_flags} suggested flag(s) still need human review."
        )
        append_audit_event(
            db, action="case_investigative_summary_read", target_type="case",
            actor_id=current_user.id, actor_role=current_user.role,
            target_id=str(case.id), case_id=case.id,
            ip=request.client.host if request.client else None,
            details={"evidence_count": len(evidence_rows)},
        )
        db.commit()
        response.headers["Cache-Control"] = "no-store"
        return {
            "case_id": str(case.id), "case_ref": case.case_ref,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overview": overview,
            "evidence_count": len(evidence_rows),
            "analysed_count": completed,
            "needs_analysis_count": not_completed,
            "pending_flag_count": pending_flags,
            "categories": sorted(category_items.values(), key=lambda item: item["category"]),
            "evidence": evidence_summary,
            "limitations": [
                "This is a deterministic rollup of stored records, not a finding that an event occurred.",
                "Selected focus categories are reporter-provided context and do not prove a category applies.",
                "Review the original evidence and extraction coverage before interpreting any snippet.",
            ],
        }

    @router.post("/evidence/{evidence_id}/analyse", status_code=status.HTTP_202_ACCEPTED)
    def request_analysis(evidence_id: UUID, request: Request,
        current_user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db_dependency)):
        _require_role(current_user, REVIEW_ROLES)
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found.")
        _require_case_access(current_user, db, evidence.case_id)
        analysis = db.scalar(select(Analysis).where(Analysis.evidence_id == evidence_id))
        if analysis is None or analysis.status not in {"done", "running"}:
            evidence.analysis_status = "pending"
            if analysis is not None:
                analysis.status = "pending"
            enqueue_analysis(db, str(evidence_id))
        append_audit_event(db, action="analysis_requested", target_type="evidence",
            actor_id=current_user.id, actor_role=current_user.role, target_id=str(evidence_id),
            case_id=evidence.case_id, ip=request.client.host if request.client else None)
        db.commit()
        analysis = db.scalar(select(Analysis).where(Analysis.evidence_id == evidence_id))
        return _analysis_json(db, evidence, analysis)

    @router.patch("/flags/{flag_id}")
    def review_flag(flag_id: UUID, payload: FlagReviewRequest, request: Request,
        current_user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db_dependency)):
        _require_role(current_user, REVIEW_ROLES)
        flag = db.get(ThreatFlag, flag_id)
        if flag is None:
            raise HTTPException(status_code=404, detail="Threat flag not found.")
        evidence = db.get(Evidence, flag.evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence not found.")
        _require_case_access(current_user, db, evidence.case_id)
        flag.review_status = payload.review_status
        flag.reviewed_by = current_user.id
        flag.reviewed_at = datetime.now(timezone.utc)
        analysis = db.scalar(select(Analysis).where(Analysis.evidence_id == evidence.id))
        feedback = dict((analysis.raw_json or {}).get("review_feedback", {})) if analysis else {}
        feedback[str(flag.id)] = {
            "review_status": payload.review_status,
            "reason": payload.review_reason,
            "reviewed_at": flag.reviewed_at.isoformat(),
        }
        if analysis is not None:
            analysis.raw_json = {**(analysis.raw_json or {}), "review_feedback": feedback}
        append_audit_event(db, action="threat_flag_review", target_type="threat_flag",
            actor_id=current_user.id, actor_role=current_user.role, target_id=str(flag.id),
            case_id=evidence.case_id, ip=request.client.host if request.client else None,
            details={"review_status": payload.review_status, "review_reason": payload.review_reason})
        db.commit()
        return _flag_json(flag)

    @router.get("/cases/{case_id}/links")
    def get_case_links(case_id: UUID, response: Response, current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency)):
        _require_role(current_user, READ_ROLES)
        case = _require_case_access(current_user, db, case_id)
        response.headers["Cache-Control"] = "no-store"
        links = db.scalars(select(CaseLink).where(or_(CaseLink.case_a_id == case_id, CaseLink.case_b_id == case_id)).order_by(CaseLink.confidence.desc(), CaseLink.id)).all()
        output = []
        for link in links:
            other_id = link.case_b_id if link.case_a_id == case_id else link.case_a_id
            output.append(_link_json(link, db.get(Case, other_id)))
        return output

    @router.post("/links", status_code=status.HTTP_201_CREATED)
    def create_manual_link(payload: LinkCreateRequest, request: Request,
        current_user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db_dependency)):
        _require_role(current_user, REVIEW_ROLES)
        left_id, right_id = payload.case_a_id, payload.case_b_id
        if left_id == right_id:
            raise HTTPException(status_code=422, detail="A case cannot be linked to itself.")
        case_a, case_b = db.get(Case, left_id), db.get(Case, right_id)
        if case_a is None or case_b is None or not can_access_case(current_user, case_a) or not can_access_case(current_user, case_b):
            raise HTTPException(status_code=404, detail="Case not found.")
        left_id, right_id = sorted((left_id, right_id), key=lambda value: value.int)
        existing = db.scalar(select(CaseLink).where(CaseLink.case_a_id == left_id, CaseLink.case_b_id == right_id))
        if existing is not None:
            return _link_json(existing, db.get(Case, right_id if left_id == payload.case_a_id else left_id))
        note = payload.note.strip() or "Manually linked by investigator."
        link = CaseLink(case_a_id=left_id, case_b_id=right_id,
            shared_entities=[{"id": f"note:{uuid4()}", "type": "note", "raw": note, "normalised": note, "confidence": 1.0}],
            confidence=.5, status="suggested", created_by=f"manual:{current_user.id}")
        db.add(link)
        db.flush()
        append_audit_event(db, action="case_link_created", target_type="case_link",
            actor_id=current_user.id, actor_role=current_user.role, target_id=str(link.id),
            case_id=left_id, ip=request.client.host if request.client else None)
        db.commit()
        db.refresh(link)
        other_id = right_id if left_id == payload.case_a_id else left_id
        return _link_json(link, db.get(Case, other_id))

    @router.patch("/links/{link_id}")
    def review_link(link_id: UUID, payload: LinkReviewRequest, request: Request,
        current_user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db_dependency)):
        _require_role(current_user, REVIEW_ROLES)
        link = db.get(CaseLink, link_id)
        if link is None:
            raise HTTPException(status_code=404, detail="Case link not found.")
        _require_case_access(current_user, db, link.case_a_id)
        _require_case_access(current_user, db, link.case_b_id)
        link.status = payload.status
        link.reviewed_by = current_user.id
        link.reviewed_at = datetime.now(timezone.utc)
        link.review_reason = payload.review_reason
        append_audit_event(db, action="case_link_review", target_type="case_link",
            actor_id=current_user.id, actor_role=current_user.role, target_id=str(link.id),
            case_id=link.case_a_id, ip=request.client.host if request.client else None,
            details={"status": payload.status, "review_reason": payload.review_reason})
        db.commit()
        return _link_json(link, db.get(Case, link.case_b_id))

    return router
