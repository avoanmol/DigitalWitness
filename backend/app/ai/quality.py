"""Describe what extraction examined; this is coverage metadata, not accuracy."""
from __future__ import annotations

from typing import Any

from backend.app.ai.extract import MAX_PDF_OCR_PAGES, MAX_TEXT_CHARS


def describe_extraction_coverage(
    mime_type: str,
    text: str,
    method: str | None,
    provenance: dict[str, Any] | None,
    video: dict[str, Any] | None,
) -> dict[str, Any]:
    mime = mime_type.split(";", 1)[0].strip().lower()
    notes: list[str] = []
    truncated = len(text) >= MAX_TEXT_CHARS
    if truncated:
        notes.append(f"Extracted text reached the {MAX_TEXT_CHARS:,}-character processing limit and may be incomplete.")

    if mime in {"video/mp4", "video/quicktime"}:
        examined = int((video or {}).get("frames_examined", 0))
        total_duration = (video or {}).get("duration_seconds")
        if examined:
            status = "sampled"
            notes.append("Only sampled video frames and their extracted text were reviewed; other frames and audio may contain missing context.")
        else:
            status = "no_text"
            notes.append("No usable text was extracted from the sampled video frames.")
        return {
            "status": status,
            "method": method,
            "characters_extracted": len(text),
            "truncated": truncated,
            "units_examined": examined,
            "units_total": None,
            "duration_seconds": total_duration,
            "notes": notes,
        }

    if mime == "application/pdf":
        page_count = (provenance or {}).get("page_count")
        examined = min(int(page_count), MAX_PDF_OCR_PAGES) if isinstance(page_count, int) else None
        if isinstance(page_count, int) and page_count > MAX_PDF_OCR_PAGES:
            notes.append(f"Only the first {MAX_PDF_OCR_PAGES} of {page_count} PDF pages were examined.")
        if text.strip():
            status = "partial" if truncated or (isinstance(page_count, int) and page_count > MAX_PDF_OCR_PAGES) else "text_extracted"
        else:
            status = "no_text"
            notes.append("No selectable or OCR-readable text was extracted from the examined pages.")
        return {
            "status": status,
            "method": method,
            "characters_extracted": len(text),
            "truncated": truncated,
            "units_examined": examined,
            "units_total": page_count,
            "notes": notes,
        }

    if text.strip():
        status = "partial" if truncated else "text_extracted"
    else:
        status = "no_text"
        if method and ("unavailable" in method or "error" in method):
            status = "extraction_failed"
            notes.append("Text extraction failed; a person should inspect the original file directly.")
        else:
            notes.append("No usable text was extracted; visual content may still be relevant.")
    return {
        "status": status,
        "method": method,
        "characters_extracted": len(text),
        "truncated": truncated,
        "units_examined": 1,
        "units_total": 1,
        "notes": notes,
    }
