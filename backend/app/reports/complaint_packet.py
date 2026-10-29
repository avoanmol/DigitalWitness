"""Render a reporter-controlled draft packet for external submission."""

from __future__ import annotations

from datetime import date, datetime, timezone
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle


INK = colors.HexColor("#183441")
TEAL = colors.HexColor("#087F80")
MUTED = colors.HexColor("#667981")
PALE = colors.HexColor("#EFF7F5")
GRID = colors.HexColor("#DCE6E8")


def _safe(value: Any, limit: int = 4000) -> str:
    text = str(value if value not in (None, "") else "Not provided")[:limit]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(character for character in text if character in "\n\t" or (ord(character) >= 32 and not 0x7F <= ord(character) <= 0x9F))
    return escape(text).replace("\n", "<br/>")


def _utc(value: datetime | None) -> str:
    if value is None:
        return "Not recorded"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _entered_time(value: str | None, timezone_note: str | None) -> str:
    if not value:
        return "Not provided"
    suffix = f" ({timezone_note})" if timezone_note else " (timezone not specified)"
    return f"{value}{suffix}"


def requires_utf8_text(
    *, case: Any, details: dict[str, Any], evidence_rows: list[dict[str, Any]], ai_notes: list[dict[str, Any]],
) -> bool:
    """Avoid rendering text the built-in PDF fonts cannot represent faithfully."""
    values: list[Any] = [case.case_ref, case.title, *details.values()]
    for row in evidence_rows:
        values.extend(row.values())
    for note in ai_notes:
        values.extend(note.values())
    for value in values:
        if value is None or isinstance(value, (int, float, bool, datetime)):
            continue
        try:
            str(value).encode("cp1252")
        except UnicodeEncodeError:
            return True
    return False


def build_complaint_packet_text(
    *,
    case: Any,
    details: dict[str, Any],
    evidence_rows: list[dict[str, Any]],
    ai_notes: list[dict[str, Any]],
    generated_at: datetime,
) -> str:
    """Create a UTF-8 text packet when the PDF's standard fonts lack a glyph."""
    channel = "National Cyber Crime Reporting Portal — https://www.cybercrime.gov.in/" if details["channel"] == "cybercrime_portal" else "Local police (selected by reporter)"
    lines = [
        "DigitalWitness — Complaint preparation",
        "DRAFT FOR REPORTER REVIEW — NOT SUBMITTED",
        "This is not an FIR, police report, or finding that an offence occurred.",
        "The reporter must review this draft and submit it themself through an official channel.",
        "",
        f"Case reference: {case.case_ref}",
        f"Case title: {case.title}",
        f"Prepared: {_utc(generated_at)}",
        f"Selected reporting channel: {channel}",
        f"Incident date: {details.get('incident_date') or 'Not provided'}",
        f"Time and timezone: {_entered_time(details.get('incident_time'), details.get('timezone_note'))}",
        f"Platform: {details.get('platform') or 'Not provided'}",
        f"Account / handle: {details.get('account_or_handle') or 'Not provided'}",
        f"Profile or content URL: {details.get('profile_url') or 'Not provided'}",
        f"State / district: {' / '.join(part for part in (details.get('state'), details.get('district')) if part) or 'Not provided'}",
        f"Local police station: {details.get('police_station') or 'Not provided'}",
        "",
        "REPORTER'S STATEMENT",
        _plain(details.get("statement")),
        "",
        "EVIDENCE MANIFEST",
        "Original files are not attached; provide them separately if requested.",
    ]
    if evidence_rows:
        for row in evidence_rows:
            lines.extend([
                f"File: {_plain(row.get('filename'))}",
                f"SHA-256: {_plain(row.get('sha256'))}",
                f"Received (UTC): {_utc(row.get('uploaded_at'))}",
                f"Integrity: {_plain(row.get('verification'))}; anchor: {_plain(row.get('anchor_status'))}",
                f"Chain: {_plain(row.get('chain_id'))}; transaction: {_plain(row.get('transaction_hash'))}",
                "",
            ])
    else:
        lines.extend(["No files attached to this case.", ""])
    lines.extend([
        "AI-ASSISTED REVIEW NOTES",
        "Automated leads only; they are not proof, a legal conclusion, or an authenticity check.",
        "A human review label does not confirm that an offence occurred.",
    ])
    if ai_notes:
        for note in ai_notes:
            lines.extend([
                f"Source: {_plain(note.get('filename'))}",
                f"Suggested category / severity: {_plain(note.get('category'))} / {_plain(note.get('severity'))}",
                f"Review status: {_plain(note.get('review_status'))}",
                f"Source excerpt: {_plain(note.get('snippet'))}",
                *([f"Reporter correction / context (not independently verified): {_plain(note.get('reporter_comment'))}"] if note.get("reporter_comment") else []),
                "",
            ])
    else:
        lines.extend(["No AI notes are recorded for this case.", ""])
    lines.extend([
        "IMPORTANT LIMITS",
        "A verified integrity result means only that a checked file matches its saved fingerprint / anchor under the recorded process. It does not prove who created the file, when its contents were created, or that screenshots, audio, or video are genuine.",
        "DigitalWitness does not determine guilt, predict criminality, or submit this complaint.",
        "Do not add Aadhaar numbers, passwords, full home addresses, or unrelated private details.",
        "The official channel may have its own form, length limits, and identity requirements. Review and adapt this draft there yourself.",
        f"Prepared by DigitalWitness for case {case.case_ref} at {_utc(generated_at)}.",
    ])
    return "\n".join(lines) + "\n"


def _plain(value: Any, limit: int = 6000) -> str:
    text = str(value if value not in (None, "") else "Not provided")[:limit]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(character for character in text if character in "\n\t" or (ord(character) >= 32 and not 0x7F <= ord(character) <= 0x9F))


def build_complaint_packet(
    *,
    case: Any,
    details: dict[str, Any],
    evidence_rows: list[dict[str, Any]],
    ai_notes: list[dict[str, Any]],
    generated_at: datetime,
) -> bytes:
    """Build a draft-only PDF; caller supplies only records from this case."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=17 * mm,
        title=f"Complaint preparation draft {case.case_ref}",
        author="DigitalWitness",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("PacketTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK, alignment=TA_LEFT, spaceAfter=2 * mm)
    heading = ParagraphStyle("PacketHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=4 * mm, spaceAfter=2 * mm)
    body = ParagraphStyle("PacketBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=INK, spaceAfter=2 * mm, wordWrap="CJK")
    small = ParagraphStyle("PacketSmall", parent=body, fontSize=7.5, leading=10, textColor=MUTED)
    alert = ParagraphStyle("PacketAlert", parent=body, fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=colors.HexColor("#7A3D12"), borderColor=colors.HexColor("#EAD3AF"), borderWidth=.7, borderPadding=8, backColor=colors.HexColor("#FFF8EA"), spaceBefore=2 * mm, spaceAfter=3 * mm)

    def para(value: Any, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(_safe(value), style)

    def table(rows: list[list[Any]], widths: list[float]) -> LongTable:
        result = LongTable(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        result.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PALE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), .35, GRID),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFCFC")]),
        ]))
        return result

    channel = "Official National Cyber Crime Reporting Portal (https://www.cybercrime.gov.in/)" if details["channel"] == "cybercrime_portal" else "Local police (selected by reporter)"
    incident_date = details.get("incident_date")
    try:
        parsed_date = date.fromisoformat(incident_date) if incident_date else None
        incident_date_display = parsed_date.strftime("%d %B %Y") if parsed_date else "Not provided"
    except (TypeError, ValueError):
        incident_date_display = str(incident_date or "Not provided")

    story: list[Any] = [
        Paragraph("DigitalWitness · Complaint preparation", ParagraphStyle("PacketBrand", parent=small, fontName="Helvetica-Bold", textColor=TEAL)),
        Paragraph("Complaint packet draft", title),
        para(f"Case reference: {case.case_ref} · Prepared: {_utc(generated_at)}", small),
        Paragraph("DRAFT FOR REPORTER REVIEW — NOT SUBMITTED. This document is not an FIR, police report, or finding that an offence occurred. The reporter must review it and submit it themself through an official channel.", alert),
        Paragraph("Reporter-entered details", heading),
        table([
            [para("Field"), para("Provided details")],
            [para("Selected reporting channel"), para(channel)],
            [para("Incident date"), para(incident_date_display)],
            [para("Time and timezone"), para(_entered_time(details.get("incident_time"), details.get("timezone_note")))],
            [para("Platform"), para(details.get("platform"))],
            [para("Account / handle"), para(details.get("account_or_handle"))],
            [para("Profile or content URL"), para(details.get("profile_url"))],
            [para("State / district"), para(" / ".join(part for part in (details.get("state"), details.get("district")) if part) or "Not provided")],
            [para("Local police station (optional)"), para(details.get("police_station"))],
        ], [51 * mm, 124 * mm]),
        Paragraph("Reporter’s statement", heading),
        para(details["statement"]),
        Paragraph("Evidence manifest", heading),
        para("This list records files already attached to this DigitalWitness case. It does not attach the original files; include those separately when reporting.", small),
    ]

    evidence_rows_pdf = [[para(value, small) for value in ("File", "SHA-256", "Received (UTC)", "Integrity / anchor status")]]
    for row in evidence_rows:
        status = row.get("verification") or "not checked"
        anchor = row.get("anchor_status") or "not anchored"
        chain_reference = f"chain {row.get('chain_id')}" if row.get("chain_id") is not None else "chain not recorded"
        transaction_reference = f"transaction {row.get('transaction_hash')}" if row.get("transaction_hash") else "transaction not recorded"
        evidence_rows_pdf.append([
            para(row.get("filename"), small),
            para(row.get("sha256"), small),
            para(_utc(row.get("uploaded_at")), small),
            para(f"{status}; {anchor}; {chain_reference}; {transaction_reference}", small),
        ])
    if len(evidence_rows_pdf) == 1:
        evidence_rows_pdf.append([para("No files attached to this case.", small), para("—", small), para("—", small), para("—", small)])
    story.append(table(evidence_rows_pdf, [46 * mm, 53 * mm, 34 * mm, 42 * mm]))

    story.extend([
        Paragraph("AI-assisted review notes", heading),
        para("These are automated suggestions linked to files in this case. They are not proof, a legal conclusion, or an authenticity check. Review the cited original content yourself; pending notes have not been reviewed by a human.", small),
    ])
    notes_rows = [[para(value, small) for value in ("Source file", "Suggested category / severity", "Review status", "Source excerpt")]]
    for note in ai_notes:
        excerpt = f"Source excerpt: {note.get('snippet') or 'Not provided'}"
        if note.get("reporter_comment"):
            excerpt += f"\nReporter correction / context (not independently verified): {note['reporter_comment']}"
        notes_rows.append([
            para(note.get("filename"), small),
            para(f"{note.get('category')} / {note.get('severity')}", small),
            para(note.get("review_status"), small),
            para(excerpt, small),
        ])
    if len(notes_rows) == 1:
        notes_rows.append([para("No AI notes to include.", small), para("—", small), para("—", small), para("—", small)])
    story.append(table(notes_rows, [38 * mm, 41 * mm, 25 * mm, 71 * mm]))

    story.extend([
        Paragraph("Important limits", heading),
        para("A “verified” integrity result means only that the checked file matches its saved fingerprint / anchor under the recorded process. It does not prove who created the file, when its contents were created, or that screenshots, audio, or video are genuine. DigitalWitness does not determine guilt, predict criminality, or submit this complaint."),
        para("The official channel may have its own fields, length limits, and identity requirements. Review and adapt this draft there yourself.", small),
        para("Do not add Aadhaar numbers, passwords, full home addresses, or unrelated private details. The original evidence files are not embedded in this packet. Keep the originals unchanged and provide them separately if the official channel asks for them.", small),
        Spacer(1, 2 * mm),
        para(f"Prepared by DigitalWitness for case {case.case_ref}. Packet digest is available in the download response. Prepared at {_utc(generated_at)}.", small),
    ])
    doc.build(story)
    return buffer.getvalue()
