from __future__ import annotations
import hashlib
import logging
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.ai.categories import clean_investigation_categories
from backend.app.ai.extract import detect_language, extract_document_text, extract_entities
from backend.app.ai.jobs import enqueue_linking
from backend.app.ai.llm_client import PROMPT_VERSION, analyse_with_llm, configured_model
from backend.app.ai.normalise import normalise_entity
from backend.app.ai.provenance import inspect_static_provenance
from backend.app.ai.quality import describe_extraction_coverage
from backend.app.ai.video import extract_video_frames
from backend.app.ai.threats import RULES_SOURCE, RULES_VERSION, context_cautions, detect_threats
from backend.models import Analysis, Entity, Evidence, ThreatFlag
from backend.security import decrypt_evidence
from backend.storage import get_encrypted_evidence

logger = logging.getLogger("digitalwitness.ai")


def _effective_mime(filename: str, mime_type: str) -> str:
    mime_type = mime_type.split(";")[0].strip().lower()
    if mime_type in {"image/jpeg", "image/png", "image/webp", "application/pdf", "video/mp4", "video/quicktime", "video/webm"}:
        return mime_type
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".pdf": "application/pdf",
            ".webp": "image/webp", ".mp4": "video/mp4", ".mov": "video/quicktime",
            ".webm": "video/webm"}.get(Path(filename).suffix.lower(), mime_type)



def _merge_llm_entities(text: str, entities: list, extracted: list) -> list:
    by_key = {(item.type, item.normalised_value): item for item in extracted}
    for item in entities:
        offset = next((index for index in range(max(0, len(text) - len(item.value) + 1)) if text[index:index + len(item.value)].casefold() == item.value.casefold()), -1)
        if offset < 0:
            continue
        raw = text[offset:offset + len(item.value)]
        normalized = normalise_entity(item.type, raw)
        if not normalized or (item.type, normalized) in by_key:
            continue
        from backend.app.ai.extract import ExtractedEntity
        candidate = ExtractedEntity(item.type, raw, normalized, item.confidence, offset, offset + len(raw))
        by_key[(item.type, normalized)] = candidate
    return list(by_key.values())


def _merge_threats(text: str, language: str, llm_result) -> list:
    found = detect_threats(text, language)
    keys = {(item.threat_class.casefold(), item.snippet) for item in found}
    if llm_result:
        from backend.app.ai.threats import ThreatCandidate
        for item in llm_result.threats:
            if item.snippet not in text:
                continue
            key = (item.threat_class.casefold(), item.snippet)
            if key not in keys:
                cautions = context_cautions(item.snippet, language)
                reason = item.reason or "AI suggestion; requires human review."
                confidence = item.confidence
                if cautions:
                    reason += " Context cues need review: " + ", ".join(cautions) + ". This does not decide whether the content is harmful."
                    confidence = min(confidence, .42)
                found.append(ThreatCandidate(item.threat_class, item.severity, item.snippet, confidence, reason, cautions))
                keys.add(key)
    return found[:100]


def analyse_evidence(evidence_id: str, session_factory) -> None:
    evidence_uuid = UUID(evidence_id)
    with session_factory() as db:
        evidence = db.get(Evidence, evidence_uuid)
        if evidence is None:
            return
        analysis = db.scalar(select(Analysis).where(Analysis.evidence_id == evidence_uuid))
        if analysis is not None and analysis.status == "done":
            evidence.analysis_status = "done"
            db.commit()
            return
        encrypted = get_encrypted_evidence(evidence.storage_key)
        if len(encrypted) < 13:
            raise ValueError("Encrypted evidence object is incomplete")
        source = decrypt_evidence(encrypted[12:], encrypted[:12])
        if hashlib.sha256(source).hexdigest() != evidence.sha256:
            raise ValueError("Evidence digest does not match its receipt")
        mime_type = _effective_mime(evidence.original_filename, evidence.mime_type)
        investigation_categories = clean_investigation_categories(
            (evidence.metadata_json or {}).get("investigation_categories", [])
        )
        video_summary = None
        frame_images: list[bytes] = []
        try:
            if mime_type in {"video/mp4", "video/quicktime", "video/webm"}:
                text, ocr_note, frame_images, video_summary = extract_video_frames(source, evidence.original_filename)
                provenance = {
                    "file_format": "video",
                    "metadata_present": bool(video_summary.get("container_creation_time_present")),
                    "observations": (["Container creation-time metadata field is present; its value is not trusted."]
                                     if video_summary.get("container_creation_time_present") else []),
                    "caveat": video_summary["caveat"],
                }
            else:
                text, ocr_note = extract_document_text(source, evidence.original_filename, mime_type)
                provenance = inspect_static_provenance(source, mime_type)
        except Exception as exc:
            logger.warning("Evidence extraction unavailable (%s); continuing with configured analysis", type(exc).__name__)
            text, ocr_note = "", f"extraction_unavailable:{type(exc).__name__}"
            provenance = {"file_format": "video" if mime_type.startswith("video/") else "unknown",
                          "metadata_present": False, "observations": [],
                          "caveat": "Metadata inspection unavailable; no authenticity conclusion is possible."}
        llm_result = None
        is_image = mime_type in {"image/jpeg", "image/png", "image/webp"}
        is_video = mime_type in {"video/mp4", "video/quicktime", "video/webm"}
        if text.strip() or is_image or (is_video and frame_images):
            try:
                llm_result = analyse_with_llm(
                    text,
                    image_bytes=source if is_image else None,
                    image_frames=frame_images if is_video else None,
                    mime_type="image/jpeg" if is_video else mime_type,
                    investigation_categories=investigation_categories,
                )
            except Exception as exc:
                # Provider errors and malformed JSON fall back to local rules without logging evidence.
                logger.warning("LLM response unavailable (%s); using local analysis", type(exc).__name__)
        if not text and llm_result:
            text = llm_result.text
        language = (llm_result.language if llm_result and llm_result.language in {"en", "hi", "kn"} else None) or detect_language(text)
        coverage = describe_extraction_coverage(mime_type, text, ocr_note, provenance, video_summary)
        if not text.strip():
            if analysis is None:
                analysis = Analysis(evidence_id=evidence_uuid, status="skipped")
                db.add(analysis)
            analysis.status = "skipped"
            analysis.text = None
            analysis.language = None
            analysis.model = configured_model()[:100] if llm_result else RULES_VERSION
            analysis.prompt_version = PROMPT_VERSION
            analysis.raw_json = {"reason": ocr_note or "No text could be extracted.",
                             "extraction_method": ocr_note, "human_review_required": True,
                             "investigation_categories": investigation_categories,
                             "provenance": provenance, "video": video_summary,
                             "coverage": coverage,
                             "review_feedback": (analysis.raw_json or {}).get("review_feedback", {})}
            evidence.analysis_status = "skipped"
            db.commit()
            return

        entities = _merge_llm_entities(text, llm_result.entities if llm_result else [], extract_entities(text))
        threats = _merge_threats(text, language, llm_result)
        if analysis is None:
            analysis = Analysis(evidence_id=evidence_uuid, status="running")
            db.add(analysis)
        analysis.text = text
        analysis.language = language
        analysis.model = configured_model()[:100] if llm_result else RULES_VERSION
        analysis.prompt_version = PROMPT_VERSION
        analysis.status = "done"
        previous_feedback = (analysis.raw_json or {}).get("review_feedback", {})
        analysis.raw_json = {
            "human_review_required": True,
            "source": "llm+rules" if llm_result else RULES_SOURCE,
            "ocr_note": ocr_note,
            "extraction_method": ocr_note,
            "investigation_categories": investigation_categories,
            "provenance": provenance,
            "video": video_summary,
            "coverage": coverage,
            "entities": len(entities),
            "threat_flags": len(threats),
            "review_feedback": previous_feedback,
        }
        existing_entities = db.scalars(select(Entity).where(Entity.evidence_id == evidence_uuid)).all()
        for item in existing_entities:
            db.delete(item)
        for item in entities:
            db.add(Entity(evidence_id=evidence_uuid, case_id=evidence.case_id, type=item.type,
                          raw_value=item.raw_value, normalised_value=item.normalised_value,
                          confidence=item.confidence, source_span={"start": item.start, "end": item.end}))

        old_flags = db.scalars(select(ThreatFlag).where(ThreatFlag.evidence_id == evidence_uuid)).all()
        reviewed_keys = {(item.threat_class.casefold(), item.snippet): item for item in old_flags if item.review_status != "pending"}
        for item in old_flags:
            if item.review_status == "pending":
                db.delete(item)
        for candidate in threats:
            key = (candidate.threat_class.casefold(), candidate.snippet)
            if key in reviewed_keys:
                continue
            if candidate.snippet not in text:
                continue
            db.add(ThreatFlag(evidence_id=evidence_uuid, threat_class=candidate.threat_class,
                              severity=candidate.severity, snippet=candidate.snippet,
                              confidence=candidate.confidence, reason=candidate.reason,
                              review_status="pending"))
        evidence.analysis_status = "done"
        enqueue_linking(db, str(evidence.case_id))
        db.commit()


def link_case(case_id: str, session_factory) -> None:
    from backend.app.ai.linking import suggest_links_for_case
    case_uuid = UUID(case_id)
    with session_factory() as db:
        suggest_links_for_case(db, case_uuid)
        db.commit()
