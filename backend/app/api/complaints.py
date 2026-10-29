"""Reporter-owned complaint packet preview and draft generation."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Any, Callable, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.reports.complaint_packet import (
    build_complaint_packet,
    build_complaint_packet_text,
    requires_utf8_text,
)
from backend.audit import append_audit_event
from backend.models import Case, Evidence, MerkleBatch, MerkleProof, ThreatFlag, User, Verification
from backend.security import decrypt_case_secret, encrypt_case_secret


class ComplaintAiNoteFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    flag_id: UUID
    include: bool = True
    reporter_comment: str | None = Field(default=None, max_length=1000)

    @field_validator("reporter_comment", mode="before")
    @classmethod
    def empty_comment_is_missing(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("reporter_comment")
    @classmethod
    def strip_control_characters(cls, value: str | None) -> str | None:
        if value is not None and any(ord(character) < 32 and character not in "\n\t" for character in value):
            raise ValueError("Comments must not contain control characters.")
        return value


class ComplaintPacketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    channel: Literal["cybercrime_portal", "local_police"]
    incident_date: str | None = Field(default=None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    incident_time: str | None = Field(default=None, max_length=5, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone_note: str | None = Field(default=None, max_length=80)
    platform: str = Field(min_length=1, max_length=120)
    account_or_handle: str | None = Field(default=None, max_length=200)
    profile_url: HttpUrl | None = None
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    police_station: str | None = Field(default=None, max_length=160)
    statement: str = Field(min_length=20, max_length=6000)
    ai_note_feedback: list[ComplaintAiNoteFeedback] = Field(default_factory=list, max_length=100)
    reviewed_evidence_and_notes: bool = False
    understands_not_submitted: bool = False

    @field_validator(
        "incident_date", "incident_time", "timezone_note", "account_or_handle",
        "profile_url", "state", "district", "police_station", mode="before",
    )
    @classmethod
    def empty_optional_values_are_missing(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("incident_date")
    @classmethod
    def validate_incident_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value

    @field_validator("ai_note_feedback")
    @classmethod
    def reject_duplicate_note_feedback(cls, value: list[ComplaintAiNoteFeedback]) -> list[ComplaintAiNoteFeedback]:
        flag_ids = [item.flag_id for item in value]
        if len(flag_ids) != len(set(flag_ids)):
            raise ValueError("Each AI note can be reviewed only once per draft.")
        return value

    @field_validator("profile_url")
    @classmethod
    def reject_url_credentials(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and (value.username or value.password):
            raise ValueError("Profile links must not include login credentials.")
        return value


class ExternalComplaintReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    channel: Literal["cybercrime_portal", "local_police"]
    reference: str = Field(min_length=3, max_length=160)

    @field_validator("reference")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("The reference must not contain control characters.")
        return value


def _reporter_case(db: Session, user: User, case_id: UUID) -> Case:
    if user.role != "reporter":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the reporter can prepare their complaint packet.")
    case = db.get(Case, case_id)
    if case is None or case.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return case


def _external_reference_summary(case: Case, *, reveal: bool = False) -> dict[str, Any]:
    ciphertext = case.external_reference_ciphertext
    nonce = case.external_reference_nonce
    if not ciphertext or not nonce or not case.external_reference_channel:
        return {"saved": False, "channel": None, "last_four": None, "updated_at": None}
    reference = decrypt_case_secret(ciphertext, nonce, str(case.id))
    summary = {
        "saved": True,
        "channel": case.external_reference_channel,
        "last_four": reference[-4:],
        "updated_at": case.external_reference_updated_at.isoformat() if case.external_reference_updated_at else None,
    }
    if reveal:
        summary["reference"] = reference
    return summary


def _case_records(db: Session, case_id: UUID) -> tuple[list[Evidence], list[dict[str, Any]]]:
    evidence = db.scalars(
        select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.uploaded_at, Evidence.id)
    ).all()
    evidence_ids = [item.id for item in evidence]
    verifications = db.scalars(
        select(Verification)
        .where(Verification.evidence_id.in_(evidence_ids))
        .order_by(Verification.checked_at.desc(), Verification.id.desc())
    ).all() if evidence_ids else []
    verification_by_id: dict[UUID, str] = {}
    for item in verifications:
        verification_by_id.setdefault(item.evidence_id, item.result)

    proofs = db.scalars(select(MerkleProof).where(MerkleProof.evidence_id.in_(evidence_ids))).all() if evidence_ids else []
    proof_by_evidence = {item.evidence_id: item for item in proofs}
    batch_ids = [item.batch_id for item in proofs]
    batches = db.scalars(select(MerkleBatch).where(MerkleBatch.id.in_(batch_ids))).all() if batch_ids else []
    batch_by_id = {item.id: item for item in batches}

    manifest: list[dict[str, Any]] = []
    for item in evidence:
        proof = proof_by_evidence.get(item.id)
        batch = batch_by_id.get(proof.batch_id) if proof else None
        manifest.append({
            "evidence_id": str(item.id),
            "filename": item.original_filename,
            "sha256": item.sha256,
            "uploaded_at": item.uploaded_at,
            "file_status": item.status,
            "analysis_status": item.analysis_status,
            "verification": verification_by_id.get(item.id, "not checked"),
            "anchor_status": batch.status if batch else "not anchored",
            "chain_id": batch.chain_id if batch else None,
            "transaction_hash": batch.tx_hash if batch else None,
        })
    return evidence, manifest


def _ai_notes(db: Session, evidence: list[Evidence]) -> list[dict[str, Any]]:
    evidence_ids = [item.id for item in evidence]
    if not evidence_ids:
        return []
    filenames = {item.id: item.original_filename for item in evidence}
    flags = db.scalars(
        select(ThreatFlag).where(
            ThreatFlag.evidence_id.in_(evidence_ids),
            ThreatFlag.review_status != "rejected",
        ).order_by(ThreatFlag.evidence_id, ThreatFlag.id)
    ).all()
    return [{
        "flag_id": str(flag.id),
        "evidence_id": str(flag.evidence_id),
        "filename": filenames.get(flag.evidence_id, "Case evidence"),
        "category": flag.threat_class,
        "severity": flag.severity,
        "review_status": flag.review_status,
        "snippet": flag.snippet[:600],
    } for flag in flags]


def _preview_payload(case: Case, evidence: list[Evidence], manifest: list[dict[str, Any]], notes: list[dict[str, Any]]) -> dict[str, Any]:
    pending_analysis = sum(item.analysis_status in {"pending", "running"} for item in evidence)
    failed_analysis = sum(item.analysis_status in {"failed", "skipped"} for item in evidence)
    return {
        "case_id": str(case.id),
        "case_ref": case.case_ref,
        "case_title": case.title,
        "incident_date_on_record": case.incident_date.isoformat() if case.incident_date else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence": manifest,
        "ai_notes": notes,
        "analysis_pending_count": pending_analysis,
        "analysis_unavailable_count": failed_analysis,
        "limitations": [
            "AI notes are automated leads and may be wrong; they do not establish that a crime occurred.",
            "Integrity status concerns the saved file fingerprint / anchor only. It does not prove the original file is authentic.",
            "Review the listed original files and excerpts. Original files are not embedded in the complaint packet.",
            "DigitalWitness does not send a complaint or select a legal outcome for you.",
        ],
    }


def create_complaints_router(*, get_db_dependency: Callable[..., Any], get_current_user_dependency: Callable[..., Any]) -> APIRouter:
    router = APIRouter()

    @router.get("/cases/{case_id}/complaint-preview")
    def complaint_preview(
        case_id: UUID,
        response: Response,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        case = _reporter_case(db, current_user, case_id)
        evidence, manifest = _case_records(db, case_id)
        response.headers["Cache-Control"] = "no-store"
        return _preview_payload(case, evidence, manifest, _ai_notes(db, evidence))

    @router.get("/cases/{case_id}/external-reference")
    def get_external_complaint_reference(
        case_id: UUID,
        response: Response,
        reveal: bool = False,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        case = _reporter_case(db, current_user, case_id)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return _external_reference_summary(case, reveal=reveal)

    @router.put("/cases/{case_id}/external-reference")
    def save_external_complaint_reference(
        case_id: UUID,
        payload: ExternalComplaintReferenceRequest,
        response: Response,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        case = _reporter_case(db, current_user, case_id)
        ciphertext, nonce = encrypt_case_secret(payload.reference, str(case.id))
        case.external_reference_ciphertext = ciphertext
        case.external_reference_nonce = nonce
        case.external_reference_channel = payload.channel
        case.external_reference_updated_at = datetime.now(timezone.utc)
        append_audit_event(
            db,
            action="complaint_reference.saved",
            target_type="case",
            actor_id=current_user.id,
            actor_role=current_user.role,
            target_id=str(case.id),
            case_id=case.id,
            # Never put the external reference itself in the audit log.
            details={"channel": payload.channel, "encrypted": True},
        )
        db.commit()
        response.headers["Cache-Control"] = "no-store"
        return _external_reference_summary(case)

    @router.delete("/cases/{case_id}/external-reference")
    def delete_external_complaint_reference(
        case_id: UUID,
        response: Response,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> dict[str, Any]:
        case = _reporter_case(db, current_user, case_id)
        had_reference = bool(case.external_reference_ciphertext)
        case.external_reference_ciphertext = None
        case.external_reference_nonce = None
        case.external_reference_channel = None
        case.external_reference_updated_at = None
        if had_reference:
            append_audit_event(
                db,
                action="complaint_reference.deleted",
                target_type="case",
                actor_id=current_user.id,
                actor_role=current_user.role,
                target_id=str(case.id),
                case_id=case.id,
                details={"deleted": True},
            )
        db.commit()
        response.headers["Cache-Control"] = "no-store"
        return _external_reference_summary(case)

    @router.post("/cases/{case_id}/complaint-packet", response_class=Response)
    def generate_complaint_packet(
        case_id: UUID,
        payload: ComplaintPacketRequest,
        current_user: User = Depends(get_current_user_dependency),
        db: Session = Depends(get_db_dependency),
    ) -> Response:
        case = _reporter_case(db, current_user, case_id)
        if not payload.reviewed_evidence_and_notes or not payload.understands_not_submitted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Review the evidence and AI notes, and confirm the packet will not be submitted automatically.",
            )
        evidence, manifest = _case_records(db, case_id)
        notes = _ai_notes(db, evidence)
        feedback_by_id = {str(item.flag_id): item for item in payload.ai_note_feedback}
        valid_flag_ids = {note["flag_id"] for note in notes}
        unknown_flag_ids = set(feedback_by_id) - valid_flag_ids
        if unknown_flag_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI note feedback must refer only to notes in this case.")
        selected_notes: list[dict[str, Any]] = []
        for note in notes:
            feedback = feedback_by_id.get(str(note["flag_id"]))
            if feedback is not None and not feedback.include:
                continue
            selected_notes.append({
                **note,
                "reporter_comment": feedback.reporter_comment if feedback else None,
            })
        notes = selected_notes
        generated_at = datetime.now(timezone.utc)
        details = payload.model_dump(exclude={"reviewed_evidence_and_notes", "understands_not_submitted", "ai_note_feedback"})
        if details.get("profile_url") is not None:
            details["profile_url"] = str(details["profile_url"])
        if payload.channel == "cybercrime_portal":
            details.update({"state": None, "district": None, "police_station": None})
        use_utf8_text = requires_utf8_text(case=case, details=details, evidence_rows=manifest, ai_notes=notes)
        if use_utf8_text:
            packet_bytes = build_complaint_packet_text(
                case=case, details=details, evidence_rows=manifest, ai_notes=notes, generated_at=generated_at,
            ).encode("utf-8")
            media_type = "text/plain; charset=utf-8"
            file_extension = "txt"
            packet_format = "utf-8-text"
        else:
            packet_bytes = build_complaint_packet(
                case=case, details=details, evidence_rows=manifest, ai_notes=notes, generated_at=generated_at,
            )
            media_type = "application/pdf"
            file_extension = "pdf"
            packet_format = "pdf"
        digest = hashlib.sha256(packet_bytes).hexdigest()
        append_audit_event(
            db,
            action="complaint_packet.generated",
            target_type="complaint_packet",
            actor_id=current_user.id,
            actor_role=current_user.role,
            target_id=str(case_id),
            case_id=case_id,
            # Intentionally omit the request IP, narrative, account, URL, and location.
            details={
                "sha256": digest,
                "channel": payload.channel,
                "format": packet_format,
                "evidence_count": len(manifest),
                "ai_note_count": len(notes),
                "reporter_comment_count": sum(bool(note.get("reporter_comment")) for note in notes),
            },
        )
        db.commit()
        return Response(
            content=packet_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="DigitalWitness-complaint-draft-{case_id.hex[:12]}.{file_extension}"',
                "X-Complaint-Packet-SHA256": digest,
                "X-Complaint-Packet-Format": packet_format,
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    return router
