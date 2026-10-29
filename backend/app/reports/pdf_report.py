"""Build a read-only PDF summary from authorized case data."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#183441")
TEAL = colors.HexColor("#087F80")
MUTED = colors.HexColor("#667981")
PALE = colors.HexColor("#EFF7F5")
GRID = colors.HexColor("#DCE6E8")


def _utc(value: datetime | None) -> str:
    if value is None:
        return "Not recorded"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _safe(value: Any, limit: int = 500) -> str:
    text = str(value if value is not None else "—")[:limit]
    return escape(text).replace("\n", "<br/>")


def _hash(value: str | None) -> str:
    if not value:
        return "Not available"
    return "<br/>".join(value[index : index + 16] for index in range(0, len(value), 16))


def _audit_review_detail(entry: Any) -> str:
    details = getattr(entry, "details", None)
    if not isinstance(details, dict):
        return "—"
    fields = (
        ("review_status", "Decision"),
        ("status", "Decision"),
        ("review_reason", "Reason"),
        ("result", "Result"),
    )
    values = [
        f"{label}: {str(details[key]).replace('_', ' ').capitalize()}"
        for key, label in fields
        if details.get(key)
    ]
    return " · ".join(values) if values else "—"


def build_case_report(
    *,
    case: Any,
    evidence_rows: list[dict[str, Any]],
    confirmed_flags: list[Any],
    unreviewed_flag_count: int,
    confirmed_links: list[Any],
    audit_rows: list[Any],
    audit_check: dict[str, Any],
    generated_at: datetime,
    case_links: list[Any] | None = None,
) -> bytes:
    """Render the report contents without loading or changing stored evidence."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title=f"DigitalWitness case report {case.case_ref}",
        author="DigitalWitness",
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle("DWTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=INK, alignment=TA_LEFT, spaceAfter=3 * mm)
    sub_style = ParagraphStyle("DWSub", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED, spaceAfter=2 * mm)
    heading_style = ParagraphStyle("DWHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=4 * mm, spaceAfter=2 * mm)
    cell_style = ParagraphStyle("DWCell", parent=base["Normal"], fontName="Helvetica", fontSize=6.2, leading=8, textColor=INK, wordWrap="CJK")
    small_style = ParagraphStyle("DWSmall", parent=cell_style, fontSize=5.8, leading=7)
    disclaimer_style = ParagraphStyle("DWDisclaimer", parent=base["Normal"], fontName="Helvetica", fontSize=7.2, leading=10, textColor=MUTED, borderColor=GRID, borderWidth=.5, borderPadding=7, backColor=colors.HexColor("#F8FAFA"))

    def cell(value: Any, style: ParagraphStyle = cell_style) -> Paragraph:
        return Paragraph(_safe(value), style)

    def grid_table(rows: list[list[Any]], widths: list[float], *, repeat: int = 1) -> LongTable:
        table = LongTable(rows, colWidths=widths, repeatRows=repeat, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PALE),
            ("TEXTCOLOR", (0, 0), (-1, 0), INK),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("LEADING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), .35, GRID),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFCFC")]),
        ]))
        return table

    story: list[Any] = [
        Paragraph("DigitalWitness", ParagraphStyle("DWBrand", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=TEAL, spaceAfter=2 * mm)),
        Paragraph(f"Case report · {_safe(case.case_ref)}", title_style),
        Paragraph(_safe(case.title), ParagraphStyle("DWCaseTitle", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=INK, spaceAfter=2 * mm)),
        Paragraph(f"Generated {_utc(generated_at)} · Status: {_safe(case.status)} · Evidence records: {len(evidence_rows)}", sub_style),
        Paragraph("INTEGRITY CHECK", heading_style),
    ]
    chain_text = "Valid" if audit_check.get("valid") else "Issue found"
    story.append(Paragraph(f"Audit chain: <b>{chain_text}</b> · {int(audit_check.get('entries_checked', 0))} entries checked", sub_style))
    story.append(Paragraph("INVESTIGATOR SUMMARY", heading_style))
    verification_results = [getattr(row.get("verification"), "result", "pending") for row in evidence_rows]
    analysis_statuses = [str(row.get("analysis_status") or "pending") for row in evidence_rows]
    focus_labels = sorted({str(label) for row in evidence_rows for label in (row.get("investigation_categories") or [])})
    metadata_rows = sum(bool((row.get("provenance") or {}).get("metadata_present")) for row in evidence_rows)
    summary_rows = [[cell("Measure"), cell("Current case")],
        [cell("Integrity checks"), cell(f"{verification_results.count('verified')} verified · {verification_results.count('pending')} pending · {verification_results.count('altered')} altered")],
        [cell("AI analysis"), cell(f"{analysis_statuses.count('done')} complete · {sum(value in {'pending', 'running'} for value in analysis_statuses)} in progress · {analysis_statuses.count('skipped')} skipped · {analysis_statuses.count('failed')} failed")],
        [cell("Human review"), cell(f"{len(confirmed_flags)} confirmed flags · {unreviewed_flag_count} pending flags · {len(confirmed_links)} confirmed links")],
        [cell("Selected investigation focus"), cell(", ".join(focus_labels) if focus_labels else "None selected")],
        [cell("Files with metadata fields observed"), cell(f"{metadata_rows} of {len(evidence_rows)}; presence is not an authenticity finding")],
    ]
    story.append(grid_table(summary_rows, [210, 490]))
    story.append(Paragraph("This summary is generated from stored integrity status, analysis metadata, and human review decisions. Automated cues remain review leads.", sub_style))
    story.append(Paragraph("EVIDENCE", heading_style))
    evidence_header = ["Filename", "SHA-256", "Size", "Uploaded (UTC)", "Batch / chain", "Anchor transaction", "Batch root", "Last verification", "Checked (UTC)"]
    evidence_data = [[Paragraph(header, cell_style) for header in evidence_header]]
    for row in evidence_rows:
        verification = row.get("verification")
        evidence_data.append([
            cell(row.get("filename")), Paragraph(_hash(row.get("sha256")), small_style),
            cell(f"{int(row.get('size_bytes', 0)):,} bytes"), cell(_utc(row.get("uploaded_at"))),
            cell(f"{row.get('batch_id') or '—'} / {row.get('chain_id') or '—'}"),
            Paragraph(_hash(row.get("tx_hash")), small_style), Paragraph(_hash(row.get("batch_root")), small_style),
            cell(getattr(verification, "result", "pending")), cell(_utc(getattr(verification, "checked_at", None))),
        ])
    if len(evidence_data) == 1:
        evidence_data.append([cell("No evidence records.")] + [cell("") for _ in evidence_header[1:]])
    story.append(grid_table(evidence_data, [68, 102, 48, 68, 64, 92, 98, 63, 67]))

    story.append(Paragraph("ANALYSIS AND SOURCE METADATA", heading_style))
    analysis_data = [[cell(value) for value in ["Evidence", "Analysis", "Language", "Extraction", "Selected focus", "File details", "Metadata observations"]]]
    for row in evidence_rows:
        provenance = row.get("provenance") or {}
        observations = " ".join(provenance.get("observations", [])) or ("Metadata fields present; no listed fields observed." if provenance.get("metadata_present") else "No listed metadata fields observed.")
        details = [str(provenance.get("file_format") or "Format unavailable")]
        dimensions = provenance.get("dimensions") or {}
        if dimensions.get("width") and dimensions.get("height"):
            details.append(f"{dimensions['width']} × {dimensions['height']} px")
        if provenance.get("page_count") is not None:
            details.append(f"{provenance['page_count']} pages")
        video = row.get("video") or {}
        if video.get("duration_seconds") is not None:
            details.append(f"Video {video['duration_seconds']}s; {video.get('frames_examined', 0)}/{video.get('frames_examined_limit', 4)} sampled frames")
        analysis_data.append([
            cell(row.get("filename")), cell(row.get("analysis_status", "pending")), cell(row.get("language") or "—"),
            cell(row.get("extraction_method") or "—"), cell(", ".join(row.get("investigation_categories") or []) or "—"), cell(" · ".join(details)), cell(observations),
        ])
    if len(analysis_data) == 1:
        analysis_data.append([cell("No evidence records.")] + [cell("") for _ in range(6)])
    story.append(grid_table(analysis_data, [82, 48, 38, 94, 108, 145, 185]))
    story.append(Paragraph("Metadata observations can be missing or manipulated. They do not establish that a file is genuine or altered.", sub_style))

    story.append(Paragraph("CONFIRMED FLAGS", heading_style))
    story.append(Paragraph(f"Confirmed flags included: {len(confirmed_flags)} · Unreviewed flags: {unreviewed_flag_count}. Rejected flags are excluded.", sub_style))
    flag_rows = [[cell(value) for value in ["Evidence", "Threat class", "Severity", "Verbatim snippet", "Confidence", "Reviewed (UTC)"]]]
    flag_rows.extend([
        [cell(getattr(flag, "evidence_id", "")), cell(getattr(flag, "threat_class", "")), cell(getattr(flag, "severity", "")), cell(getattr(flag, "snippet", "")), cell(f"{float(getattr(flag, 'confidence', 0)):.0%}"), cell(_utc(getattr(flag, "reviewed_at", None)))]
        for flag in confirmed_flags
    ])
    if len(flag_rows) == 1:
        flag_rows.append([cell("No confirmed flags.")] + [cell("") for _ in range(5)])
    story.append(grid_table(flag_rows, [80, 95, 52, 286, 55, 114]))

    story.append(Paragraph("RELATED CASE LINKS AND REVIEW DECISIONS", heading_style))
    link_rows = [[cell(value) for value in ["Related case IDs", "Shared entities", "Decision", "Reason", "Reviewer ID", "Reviewed (UTC)"]]]
    links_to_report = case_links if case_links is not None else confirmed_links
    for link in links_to_report:
        shared = getattr(link, "shared_entities", None) or []
        shared_text = ", ".join(str(item.get("raw", item.get("normalised", item))) if isinstance(item, dict) else str(item) for item in shared)
        reason = str(getattr(link, "review_reason", None) or "Not reviewed").replace("_", " ").capitalize()
        reviewer = getattr(link, "reviewed_by", None)
        link_rows.append([
            cell(f"{link.case_a_id} ↔ {link.case_b_id}"), cell(shared_text),
            cell(getattr(link, "status", "suggested")), cell(reason),
            cell(reviewer if reviewer else "Not recorded"), cell(_utc(getattr(link, "reviewed_at", None))),
        ])
    if len(link_rows) == 1:
        link_rows.append([cell("No related case links.")] + [cell("") for _ in range(5)])
    story.append(grid_table(link_rows, [145, 235, 55, 115, 100, 95]))

    story.append(PageBreak())
    story.append(Paragraph("CHAIN OF CUSTODY", heading_style))
    custody_rows = [[cell(value) for value in ["Seq.", "Actor role", "Action", "Target", "Review detail", "Time (UTC)", "Entry hash"]]]
    for entry in audit_rows:
        custody_rows.append([
            cell(getattr(entry, "seq", "")), cell(getattr(entry, "actor_role", None) or "System"),
            cell(getattr(entry, "action", "")), cell(f"{getattr(entry, 'target_type', '')} / {getattr(entry, 'target_id', '') or ''}"),
            cell(_audit_review_detail(entry)), cell(_utc(getattr(entry, "created_at", None))),
            Paragraph(_hash(getattr(entry, "entry_hash", None)), small_style),
        ])
    if len(custody_rows) == 1:
        custody_rows.append([cell("No custody events are recorded.")] + [cell("") for _ in range(6)])
    story.append(grid_table(custody_rows, [34, 58, 87, 140, 106, 76, 228]))
    story.extend([
        Spacer(1, 6 * mm),
        Paragraph("WHAT THESE CHECKS MEAN", heading_style),
        Paragraph("A Verified result means the file is unchanged since anchoring. It does not establish who created the file or whether its contents are accurate. An Altered result means the current file hash differs from the recorded hash. A Pending result means the file has not yet been anchored; it is not an alarm. AI flags and case links are suggestions for human review, not findings.", disclaimer_style),
        Spacer(1, 3 * mm),
        Paragraph("This report contains sensitive case information. Share it only with authorized recipients. All timestamps in this report are UTC.", sub_style),
    ])

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(GRID)
        canvas.line(14 * mm, 12 * mm, landscape(A4)[0] - 14 * mm, 12 * mm)
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(MUTED)
        canvas.drawString(14 * mm, 8 * mm, f"DigitalWitness · {_safe(case.case_ref)} · generated {_utc(generated_at)}")
        canvas.drawRightString(landscape(A4)[0] - 14 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
