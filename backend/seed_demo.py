"""Seed clearly synthetic example cases in a deliberately opted-in database."""

from __future__ import annotations

import hashlib
import argparse
import os
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import select

from backend.app.ai.jobs import enqueue_analysis
from backend.app.ai.categories import INVESTIGATION_CATEGORIES
from backend.app.receipts import iso_utc, sign_receipt
from backend.auth import hash_password
from backend.audit import append_audit_event
from backend.database import SessionLocal
from backend.models import Case, Evidence, User
from backend.security import encrypt_evidence
from backend.storage import store_encrypted_evidence


DEMO_USERS = (
    ("demo.reporter@example.com", "Synthetic Reporter", "reporter"),
    ("demo.investigator@example.com", "Synthetic Investigator", "investigator"),
    ("demo.legal@example.com", "Synthetic Legal Reviewer", "legal"),
    ("demo.admin@example.com", "Synthetic Administrator", "admin"),
)

LEGACY_DEMO_EMAILS = {
    "demo.reporter@example.com": "demo.reporter@example.test",
    "demo.investigator@example.com": "demo.investigator@example.test",
    "demo.legal@example.com": "demo.legal@example.test",
    "demo.admin@example.com": "demo.admin@example.test",
}

SAMPLES = (
    ("DW-DEMO-2026-001", "Repeated unwanted contact", "cyberstalking_bullying",
     "Synthetic training example only. A fictional account @demo_shared_contact sent repeated unwanted messages after being asked to stop. The message says: I will find you. This text is fabricated for software demonstration."),
    ("DW-DEMO-2026-002", "Coercive payment message", "blackmail_threatening",
     "Synthetic training example only. A fictional sender demands money and writes: pay or else. The sender also threatens to expose private information. This text is fabricated for software demonstration."),
    ("DW-DEMO-2026-003", "Threat to share private images", "intimate_image_abuse",
     "Synthetic training example only. A fictional sender threatens to share your private images without permission. No image is included or described. This text is fabricated for software demonstration."),
    ("DW-DEMO-2026-004", "Alleged altered image and false claim", "defamation_morphing",
     "Synthetic training example only. A fictional post contains a false accusation about you and claims it is based on a fake image of you. The original image is not included, so authenticity cannot be assessed. This text is fabricated for software demonstration."),
    ("DW-DEMO-2026-005", "Impersonating profile", "fake_profile_impersonation",
     "Synthetic training example only. A fictional account is pretending to be you and contacting other people using a fake account in your name. This text is fabricated for software demonstration."),
    ("DW-DEMO-2026-006", "Benign awareness message", None,
     "Synthetic negative example. This fictional digital-safety workshop explains how to report unwanted messages. No threat, demand, or impersonation is present in this example."),
)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set before seeding synthetic demo records.")
    return value


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--users-only",
        action="store_true",
        help="Create the four synthetic role accounts without adding cases or evidence.",
    )
    args = parser.parse_args()
    if os.getenv("DW_ENABLE_SYNTHETIC_SEED", "").casefold() != "true":
        raise SystemExit("Set DW_ENABLE_SYNTHETIC_SEED=true only for a development/demo database.")
    if os.getenv("APP_ENV", "development").casefold() in {"production", "prod"}:
        raise SystemExit("Synthetic data seeding is disabled in production.")
    demo_password = _required("DW_DEMO_PASSWORD")
    if len(demo_password) < 12 or len(demo_password) > 128:
        raise RuntimeError("DW_DEMO_PASSWORD must contain 12 to 128 characters.")
    if not args.users_only:
        _required("RECEIPT_HMAC_KEY")
    created_users = created_cases = created_evidence = 0

    with SessionLocal() as db:
        user_by_role: dict[str, User] = {}
        for email, name, role in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == email))
            legacy = db.scalar(select(User).where(User.email == LEGACY_DEMO_EMAILS[email]))
            if user is not None and legacy is not None:
                raise RuntimeError(f"Both current and legacy synthetic demo accounts exist for role {role}; resolve the duplicate first.")
            if user is None and legacy is not None:
                if legacy.role != role:
                    raise RuntimeError(f"Existing synthetic account {legacy.email} has an unexpected role; refusing to rename it.")
                legacy.email = email
                user = legacy
            if user is None:
                user = User(email=email, full_name=name, password_hash=hash_password(demo_password), role=role, is_active=True)
                db.add(user)
                db.flush()
                created_users += 1
            elif user.role != role:
                raise RuntimeError(f"Existing synthetic account {email} has an unexpected role; refusing to change it.")
            else:
                # This opt-in development-only seed also restores the shared local demo password.
                user.password_hash = hash_password(demo_password)
            user_by_role[role] = user

        reporter = user_by_role["reporter"]
        for index, (case_ref, title, category, text) in enumerate(() if args.users_only else SAMPLES):
            case = db.scalar(select(Case).where(Case.case_ref == case_ref))
            if case is None:
                case = Case(case_ref=case_ref, title=title, description="Synthetic demo material. No real person or incident.", status="open", created_by=reporter.id)
                db.add(case)
                db.flush()
                created_cases += 1
            raw = text.encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            existing = db.scalar(select(Evidence).where(Evidence.case_id == case.id, Evidence.sha256 == digest))
            if existing:
                continue
            evidence_id = uuid4()
            timestamp = datetime.now(timezone.utc)
            storage_key = f"cases/{case.id}/evidence/{evidence_id.hex}"
            receipt_payload = {
                "receipt_id": str(evidence_id), "case_ref": case.case_ref,
                "case_id": str(case.id), "evidence_id": str(evidence_id),
                "filename": f"synthetic-example-{index + 1}.txt", "mime_type": "text/plain",
                "size_bytes": len(raw), "sha256": digest,
                "uploaded_at": iso_utc(timestamp), "status": "stored",
                "investigation_categories": [category] if category in INVESTIGATION_CATEGORIES else [],
            }
            ciphertext, nonce = encrypt_evidence(raw)
            store_encrypted_evidence(storage_key, nonce + ciphertext)
            evidence = Evidence(
                id=evidence_id, case_id=case.id, uploader_id=reporter.id,
                original_filename=receipt_payload["filename"], mime_type="text/plain",
                size_bytes=len(raw), sha256=digest, storage_key=storage_key,
                status="stored", analysis_status="pending", uploaded_at=timestamp,
                metadata_json={"encryption": "AES-256-GCM", "nonce_bytes": len(nonce),
                               "investigation_categories": receipt_payload["investigation_categories"],
                               "receipt_payload": receipt_payload, "synthetic_demo": True},
                receipt_signature=sign_receipt(receipt_payload),
            )
            db.add(evidence)
            db.flush()
            enqueue_analysis(db, str(evidence.id))
            append_audit_event(db, action="demo.synthetic_evidence.seed", target_type="evidence",
                               actor_id=user_by_role["admin"].id, actor_role="admin",
                               target_id=str(evidence.id), case_id=case.id,
                               details={"synthetic": True, "sha256": digest})
            created_evidence += 1
        db.commit()

    print(f"Synthetic demo seed complete: {created_users} users, {created_cases} cases, {created_evidence} evidence files added.")
    if not args.users_only:
        print("Cases include five investigator focus categories and one benign negative example; the shared contact is fictional.")


if __name__ == "__main__":
    main()
