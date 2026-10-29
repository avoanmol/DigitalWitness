"""Synthetic end-to-end test of the isolated AI review workflow."""

from __future__ import annotations

import os
import sys
import time
import json
import io
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from pypdf import PdfReader
from sqlalchemy import select, text

from backend.auth import create_access_token, hash_password
from backend.database import SessionLocal, engine
from backend.models import AuditLog, Case, User
from backend.security import decrypt_case_secret


def guard() -> None:
    assert os.getenv("DW_INTEGRITY_TEST_MODE") == "1", "Requires isolated test mode"
    assert engine.url.host == "db" and engine.url.database == "dw_integrity_test"
    assert os.getenv("CHAIN_RPC_URL") == "http://chain:8545"
    with engine.connect() as db:
        assert db.scalar(text("select current_database()")) == "dw_integrity_test"


def main() -> None:
    guard()
    run = uuid4().hex[:10]
    client = httpx.Client(base_url="http://api:8000", timeout=30)
    password = "Synthetic-only-password-1234"
    reporter_email = f"ai-{run}-reporter@example.com"
    registration = client.post("/auth/register", json={
        "email": reporter_email, "full_name": "Synthetic Reporter", "password": password,
    })
    assert registration.status_code == 201 and registration.json()["role"] == "reporter", registration.text
    login = client.post("/auth/login", json={"email": reporter_email, "password": password})
    assert login.status_code == 200 and login.json()["token_type"] == "bearer", login.text
    reporter_auth = {"Authorization": "Bearer " + login.json()["access_token"]}
    profile = client.get("/auth/me", headers=reporter_auth)
    assert profile.status_code == 200 and profile.json()["email"] == reporter_email, profile.text
    first_case = client.post("/cases", headers=reporter_auth,
                            json={"title": "Synthetic harassment lead A", "description": "Synthetic only."})
    second_case = client.post("/cases", headers=reporter_auth,
                             json={"title": "Synthetic harassment lead B", "description": "Synthetic only."})
    assert first_case.status_code == 201, first_case.text
    assert second_case.status_code == 201, second_case.text
    first_id, second_id = first_case.json()["id"], second_case.json()["id"]

    with SessionLocal() as db:
        investigator = User(email=f"ai-{run}-investigator@example.test", full_name="Synthetic Investigator",
                            password_hash=hash_password(password), role="investigator")
        db.add(investigator)
        db.flush()
        db.commit()
        db.refresh(investigator)

    investigator_auth = {"Authorization": "Bearer " + create_access_token(investigator.id, investigator.role)}
    print("PASS: public signup, login, profile, and reporter case creation", flush=True)

    def upload(case_id: str, content: str) -> str:
        response = client.post(
            "/evidence/upload",
            params={"case_id": case_id},
            headers=reporter_auth,
            files={"file": ("synthetic-message.txt", content.encode("utf-8"), "text/plain")},
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    first_evidence = upload(
        first_id,
        "The message says: I will share your private photos unless you pay. "
        "Contact witness@example.test.",
    )
    second_evidence = upload(
        second_id,
        "The sender used witness@example.test to contact me about a profile.",
    )

    deadline = time.monotonic() + 30
    first_analysis = second_analysis = None
    while time.monotonic() < deadline:
        first_response = client.get(f"/evidence/{first_evidence}/analysis", headers=investigator_auth)
        second_response = client.get(f"/evidence/{second_evidence}/analysis", headers=investigator_auth)
        assert first_response.status_code == 200, first_response.text
        assert second_response.status_code == 200, second_response.text
        first_analysis, second_analysis = first_response.json(), second_response.json()
        if first_analysis["status"] == "done" and second_analysis["status"] == "done":
            break
        time.sleep(.25)
    assert first_analysis and first_analysis["status"] == "done", first_analysis
    assert second_analysis and second_analysis["status"] == "done", second_analysis
    assert any(item["normalised"] == "witness@example.test" for item in first_analysis["entities"])
    assert any(item["normalised"] == "witness@example.test" for item in second_analysis["entities"])
    flag = next((item for item in first_analysis["flags"] if item["threat_class"] == "intimate_image_abuse"), None)
    assert flag and flag["review_status"] == "pending" and flag["snippet"] in first_analysis["text"]
    assert client.get(f"/evidence/{first_evidence}/analysis", headers=reporter_auth).status_code == 403
    print("PASS: AI worker extracts text/entities and stores an exact-source pending flag", flush=True)

    link = None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        links_response = client.get(f"/cases/{first_id}/links", headers=investigator_auth)
        assert links_response.status_code == 200, links_response.text
        link = next((item for item in links_response.json()
                     if {item["case_a_id"], item["case_b_id"]} == {first_id, second_id}), None)
        if link:
            break
        time.sleep(.25)
    assert link and link["status"] == "suggested", link
    assert any(item.get("normalised") == "witness@example.test" for item in link["shared_entities"])
    print("PASS: shared entity creates a human-reviewable suggested cross-case link", flush=True)

    summary_response = client.get(f"/cases/{first_id}/investigative-summary", headers=investigator_auth)
    assert summary_response.status_code == 200, summary_response.text
    summary = summary_response.json()
    assert summary["evidence_count"] == 1 and summary["analysed_count"] == 1
    assert summary["pending_flag_count"] == len(first_analysis["flags"])
    assert summary["limitations"]
    print("PASS: case summary links to saved evidence, extraction coverage, and pending review", flush=True)

    complaint_preview = client.get(f"/cases/{first_id}/complaint-preview", headers=reporter_auth)
    assert complaint_preview.status_code == 200, complaint_preview.text
    preview = complaint_preview.json()
    assert preview["case_id"] == first_id and len(preview["evidence"]) == 1
    assert preview["evidence"][0]["evidence_id"] == first_evidence
    assert any(note["snippet"] == flag["snippet"] for note in preview["ai_notes"])
    assert "text" not in preview and "description" not in preview
    assert client.get(f"/cases/{first_id}/complaint-preview", headers=investigator_auth).status_code == 403
    assert preview["ai_notes"] and preview["ai_notes"][0]["flag_id"]

    other_email = f"ai-{run}-other-reporter@example.com"
    other_registration = client.post("/auth/register", json={
        "email": other_email, "full_name": "Other Synthetic Reporter", "password": password,
    })
    assert other_registration.status_code == 201, other_registration.text
    other_login = client.post("/auth/login", json={"email": other_email, "password": password})
    other_auth = {"Authorization": "Bearer " + other_login.json()["access_token"]}
    foreign_case = client.post("/cases", headers=other_auth,
                               json={"title": "Synthetic private case", "description": "Synthetic only."})
    assert other_login.status_code == 200 and foreign_case.status_code == 201
    assert client.get(f"/cases/{foreign_case.json()['id']}/complaint-preview", headers=reporter_auth).status_code == 404

    packet_payload = {
        "channel": "cybercrime_portal",
        "incident_date": "2026-10-01",
        "incident_time": "18:20",
        "timezone_note": "India Standard Time",
        "platform": "Synthetic chat service",
        "account_or_handle": "synthetic_sender",
        "profile_url": "https://example.test/synthetic_sender",
        "state": "Synthetic state",
        "district": "Synthetic district",
        "statement": "Synthetic reporter statement for packet acceptance testing only.",
        "ai_note_feedback": [{
            "flag_id": preview["ai_notes"][0]["flag_id"],
            "include": True,
            "reporter_comment": "Synthetic reporter context note for acceptance testing.",
        }],
    }
    not_reviewed = client.post(f"/cases/{first_id}/complaint-packet", headers=reporter_auth, json=packet_payload)
    assert not_reviewed.status_code == 400, not_reviewed.text
    extra_identity = client.post(
        f"/cases/{first_id}/complaint-packet", headers=reporter_auth,
        json={**packet_payload, "aadhaar_number": "000000000000", "reviewed_evidence_and_notes": True, "understands_not_submitted": True},
    )
    assert extra_identity.status_code == 422, extra_identity.text
    packet = client.post(
        f"/cases/{first_id}/complaint-packet", headers=reporter_auth,
        json={**packet_payload, "reviewed_evidence_and_notes": True, "understands_not_submitted": True},
    )
    assert packet.status_code == 200 and packet.headers.get("content-type", "").startswith("application/pdf"), packet.text[:500]
    assert packet.content.startswith(b"%PDF-")
    assert packet.headers.get("Cache-Control") == "no-store"
    assert packet.headers.get("X-Complaint-Packet-SHA256") == sha256(packet.content).hexdigest()
    extracted_packet = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(packet.content)).pages)
    normalized_packet_text = " ".join(extracted_packet.split())
    assert "DRAFT FOR REPORTER REVIEW" in normalized_packet_text
    assert "NOT SUBMITTED" in normalized_packet_text and packet_payload["statement"] in normalized_packet_text
    assert "synthetic-message.txt" in normalized_packet_text and " ".join(flag["snippet"].split()) in normalized_packet_text
    with SessionLocal() as db:
        audit = db.scalar(select(AuditLog).where(
            AuditLog.case_id == UUID(first_id),
            AuditLog.action == "complaint_packet.generated",
        ).order_by(AuditLog.seq.desc()))
        assert audit is not None
        assert set(audit.details) == {"sha256", "channel", "format", "evidence_count", "ai_note_count", "reporter_comment_count"}
        assert audit.details["format"] == "pdf"
        assert audit.details["reporter_comment_count"] == 1
        assert packet_payload["statement"] not in json.dumps(audit.details)
        assert packet_payload["account_or_handle"] not in json.dumps(audit.details)
        assert packet_payload["ai_note_feedback"][0]["reporter_comment"] not in json.dumps(audit.details)
    assert "Synthetic reporter context note" in normalized_packet_text
    omitted_notes_packet = client.post(
        f"/cases/{first_id}/complaint-packet", headers=reporter_auth,
        json={
            **packet_payload,
            "ai_note_feedback": [{"flag_id": note["flag_id"], "include": False} for note in preview["ai_notes"]],
            "reviewed_evidence_and_notes": True,
            "understands_not_submitted": True,
        },
    )
    assert omitted_notes_packet.status_code == 200, omitted_notes_packet.text[:500]
    omitted_text = " ".join("\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(omitted_notes_packet.content)).pages).split())
    assert "No AI notes to include" in omitted_text
    hindi_statement = "यह synthetic example है: someone sent me repeated unwanted messages."
    unicode_packet = client.post(
        f"/cases/{first_id}/complaint-packet", headers=reporter_auth,
        json={**packet_payload, "statement": hindi_statement, "reviewed_evidence_and_notes": True, "understands_not_submitted": True},
    )
    assert unicode_packet.status_code == 200, unicode_packet.text[:500]
    assert unicode_packet.headers.get("content-type", "").startswith("text/plain")
    assert unicode_packet.headers.get("X-Complaint-Packet-Format") == "utf-8-text"
    assert hindi_statement in unicode_packet.content.decode("utf-8")
    assert unicode_packet.headers.get("X-Complaint-Packet-SHA256") == sha256(unicode_packet.content).hexdigest()
    with SessionLocal() as db:
        unicode_audit = db.scalar(select(AuditLog).where(
            AuditLog.case_id == UUID(first_id),
            AuditLog.action == "complaint_packet.generated",
        ).order_by(AuditLog.seq.desc()))
        assert unicode_audit is not None and unicode_audit.details["format"] == "utf-8-text"
        assert hindi_statement not in json.dumps(unicode_audit.details, ensure_ascii=False)

    external_reference_value = "NCRP-DWTEST-2026-1234"
    external_get_url = f"/cases/{first_id}/external-reference"
    assert client.get(external_get_url, headers=investigator_auth).status_code == 403
    assert client.get(f"/cases/{foreign_case.json()['id']}/external-reference", headers=reporter_auth).status_code == 404
    saved_reference = client.put(
        external_get_url,
        headers=reporter_auth,
        json={"channel": "cybercrime_portal", "reference": external_reference_value},
    )
    assert saved_reference.status_code == 200, saved_reference.text
    assert saved_reference.json()["saved"] is True and saved_reference.json()["last_four"] == "1234"
    assert external_reference_value not in saved_reference.text
    read_reference = client.get(external_get_url, headers=reporter_auth)
    assert read_reference.status_code == 200 and read_reference.json()["last_four"] == "1234"
    assert "reference" not in read_reference.json()
    revealed_reference = client.get(external_get_url + "?reveal=true", headers=reporter_auth)
    assert revealed_reference.status_code == 200 and revealed_reference.json()["reference"] == external_reference_value
    with SessionLocal() as db:
        case_row = db.get(Case, UUID(first_id))
        assert case_row is not None and external_reference_value.encode() not in case_row.external_reference_ciphertext
        assert decrypt_case_secret(case_row.external_reference_ciphertext, case_row.external_reference_nonce, first_id) == external_reference_value
        saved_audit = db.scalar(select(AuditLog).where(
            AuditLog.case_id == UUID(first_id), AuditLog.action == "complaint_reference.saved",
        ).order_by(AuditLog.seq.desc()))
        assert saved_audit is not None and external_reference_value not in json.dumps(saved_audit.details)
    removed_reference = client.delete(external_get_url, headers=reporter_auth)
    assert removed_reference.status_code == 200 and removed_reference.json()["saved"] is False
    print("PASS: reporter can include or correct draft-only AI notes and optionally save/remove an encrypted external reference", flush=True)

    reviewed = client.patch(
        f"/flags/{flag['id']}", headers=investigator_auth,
        json={"review_status": "confirmed", "review_reason": "source_supports_flag"},
    )
    assert reviewed.status_code == 200 and reviewed.json()["review_status"] == "confirmed", reviewed.text
    reviewed_link = client.patch(
        f"/links/{link['id']}", headers=investigator_auth,
        json={"status": "confirmed", "review_reason": "source_supports_connection"},
    )
    assert reviewed_link.status_code == 200 and reviewed_link.json()["status"] == "confirmed", reviewed_link.text
    insights = client.get("/ai/review-insights", headers=investigator_auth)
    assert insights.status_code == 200 and insights.json()["training_enabled"] is False, insights.text
    assert insights.json()["outcomes"]["confirmed"] == 1
    print("PASS: investigator review is recorded; feedback does not auto-train the model", flush=True)

    reporter_report = client.get(f"/cases/{first_id}/report", headers=reporter_auth)
    assert reporter_report.status_code == 403, reporter_report.text
    report = client.get(f"/cases/{first_id}/report", headers=investigator_auth)
    assert report.status_code == 200 and report.headers.get("content-type", "").startswith("application/pdf")
    assert report.content.startswith(b"%PDF-")
    assert report.headers.get("X-Report-SHA256") == sha256(report.content).hexdigest()
    print("PASS: case PDF report is role-protected and its digest is returned", flush=True)


if __name__ == "__main__":
    main()
