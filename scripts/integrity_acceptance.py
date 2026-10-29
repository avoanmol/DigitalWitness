"""Guide Gate 1 checks against isolated HTTP API, Postgres, S3 and Hardhat.

Run ONLY with compose.integrity-test.yml. Never accepts a target URL or real credentials.
The privileged hash-corruption case is guarded by the isolated database identity.
"""
import io
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from pypdf import PdfReader, PdfWriter
from sqlalchemy import select, text, func
from sqlalchemy.exc import DBAPIError
from backend.auth import create_access_token, hash_password
from backend.audit import verify_audit_chain
from backend.database import SessionLocal, engine
from backend.models import User, Case, Evidence, MerkleProof, MerkleBatch, Verification, AuditLog
from backend.security import encrypt_evidence
from backend.storage import get_encrypted_evidence, store_encrypted_evidence, delete_encrypted_evidence
from backend.app.integrity.batcher import anchor_persisted_evidence_records
from backend.app.integrity.chain import anchor_root, get_chain_id

RESULT = Path("/results/integrity-validation.json")

def guard():
    assert os.getenv("DW_INTEGRITY_TEST_MODE") == "1", "Requires isolated test mode"
    assert engine.url.host == "db" and engine.url.database == "dw_integrity_test"
    assert os.getenv("MINIO_BUCKET") == "dw-integrity-test"
    assert os.getenv("CHAIN_RPC_URL") == "http://chain:8545"
    with engine.connect() as db:
        assert db.scalar(text("select current_database()")) == "dw_integrity_test"


def pdf_bytes(label):
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    writer.add_metadata({"/Title": label})
    out = io.BytesIO(); writer.write(out)
    return out.getvalue()


def main():
    guard()
    client = httpx.Client(base_url="http://api:8000", timeout=30)
    checks = []
    def passed(name):
        checks.append({"check": name, "passed": True})
        print("PASS:", name, flush=True)
    def auth(user):
        return {"Authorization": "Bearer " + create_access_token(user.id, user.role)}
    def verify(evidence_id, user, expected):
        response = client.post(f"/evidence/{evidence_id}/verify", headers=auth(user))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["result"] == expected, body
        assert body["checked_at"].endswith("Z")
        with SessionLocal() as db:
            stored = db.get(Verification, UUID(body["verification_id"]))
            assert stored.result == expected
            event = db.scalar(select(AuditLog).where(AuditLog.action == "evidence.verify",
                AuditLog.details["verification_id"].astext == body["verification_id"]))
            assert event and event.details["result"] == expected
        return body
    if "--outage" in sys.argv:
        result = json.loads(RESULT.read_text())
        with SessionLocal() as db:
            evidence = db.get(Evidence, UUID(result["outage_evidence_id"]))
            user = db.get(User, evidence.uploader_id)
        verify(evidence.id, user, "error")
        passed("10: stopped chain returns error and persists an audited verification")
        with SessionLocal() as db:
            assert verify_audit_chain(db)["valid"]
        result["checks"].extend(checks); result["all_ten_guide_cases_passed"] = True
        RESULT.write_text(json.dumps(result, indent=2))
        return
    assert get_chain_id() == 31337
    run = uuid4().hex[:10]
    with SessionLocal() as db:
        users = {}
        password = hash_password("Synthetic-only-password-1234")
        for role in ["reporter", "other", "investigator", "legal", "admin"]:
            user = User(email=f"{run}-{role}@example.com", full_name="Synthetic integrity check",
                        password_hash=password, role="reporter" if role == "other" else role)
            db.add(user); db.flush(); users[role] = user
        case = Case(case_ref=f"DW-INT-{run}", title="Disposable integrity acceptance", created_by=users["reporter"].id)
        db.add(case); db.flush(); case_id = str(case.id)
        db.commit()
        for user in users.values(): db.refresh(user)
    reporter = users["reporter"]
    def upload(data, name="synthetic.pdf"):
        response = client.post("/evidence/upload", params={"case_id":case_id}, headers=auth(reporter),
                               files={"file":(name, data, "application/pdf")})
        assert response.status_code == 201, response.text
        return response.json()["id"]
    def anchor(ids):
        with SessionLocal() as db:
            rows = db.execute(select(Evidence.id,Evidence.uploaded_at,Evidence.status,Evidence.sha256)
                              .where(Evidence.id.in_([UUID(value) for value in ids]))).mappings().all()
            records = [dict(row) for row in rows]
        return anchor_persisted_evidence_records(records, SessionLocal)
    raw = pdf_bytes("original")
    pending_id = upload(raw)
    file_response = client.get(f"/evidence/{pending_id}/file", headers=auth(reporter))
    assert file_response.status_code == 200 and file_response.content == raw
    assert file_response.headers.get("cache-control", "").startswith("no-store")
    receipt_response = client.get(f"/evidence/{pending_id}/receipt", headers=auth(reporter))
    assert receipt_response.status_code == 200, receipt_response.text
    receipt_body = receipt_response.json()
    assert receipt_body["signature_valid"] is True and receipt_body["sha256"] == sha256(raw).hexdigest()
    verify(pending_id, reporter, "pending")
    pending_proof = client.get(f"/evidence/{pending_id}/proof", headers=auth(reporter)).json()
    assert pending_proof["status"] == "pending" and pending_proof["proof"] is None
    passed("9: uploaded evidence is pending, with an audited pending proof response")
    saved_ids = []
    for size in [1, 2, 3, 7, 10]:
        ids = [upload(raw) for _ in range(size)]
        result = anchor(ids)
        for evidence_id in ids: verify(evidence_id, reporter, "verified")
        saved_ids.extend(ids)
    passed("8: clean batches of sizes 1, 2, 3, 7 and 10 verify through HTTP and storage")
    target = saved_ids[1]  # a two-leaf batch, so a proof sibling exists
    with SessionLocal() as db:
        evidence = db.get(Evidence, UUID(target)); storage_key = evidence.storage_key
        proof = db.get(MerkleProof, UUID(target)); batch_id = proof.batch_id
        original_proof = list(proof.proof)
        original_hash = evidence.sha256
    encrypted = get_encrypted_evidence(storage_key)
    def replace_bytes(data):
        cipher, nonce = encrypt_evidence(data)
        store_encrypted_evidence(storage_key, nonce+cipher)
    def restore(): store_encrypted_evidence(storage_key, encrypted)
    changed = bytes([raw[0] ^ 1]) + raw[1:]
    replace_bytes(changed); verify(target, reporter, "altered"); restore()
    passed("1: flip one plaintext byte, re-encrypt, and detect alteration")
    replace_bytes(b"X" * len(raw)); verify(target, reporter, "altered"); restore()
    passed("2: same-name same-size replacement is altered")
    with SessionLocal() as db:
        try:
            db.execute(text("update evidence set sha256=:hash where id=:id"), {"hash":sha256(changed).hexdigest(),"id":target})
            db.commit()
            raise AssertionError("immutability trigger failed")
        except DBAPIError: db.rollback()
    passed("protected evidence hash rejects normal SQL updates")
    replace_bytes(changed)
    # Model privileged DB compromise in this disposable database only. This is
    # never used by application code and never disables a trigger globally.
    with SessionLocal() as db:
        db.execute(text("SET LOCAL session_replication_role = replica"))
        db.execute(text("update evidence set sha256=:hash where id=:id"), {"hash":sha256(changed).hexdigest(),"id":target})
        db.commit()
    verify(target, reporter, "altered")
    with SessionLocal() as db:
        db.execute(text("SET LOCAL session_replication_role = replica"))
        db.execute(text("update evidence set sha256=:hash where id=:id"), {"hash":original_hash,"id":target})
        db.commit()
    restore(); passed("3: changed file plus forged DB hash still fails its Merkle proof")
    with SessionLocal() as db:
        proof = db.get(MerkleProof, UUID(target))
        proof.proof = [{**original_proof[0], "hash":"00"*32}, *original_proof[1:]]; db.commit()
    verify(target, reporter, "altered")
    with SessionLocal() as db:
        db.get(MerkleProof, UUID(target)).proof = original_proof; db.commit()
    passed("4: modified proof sibling is altered")
    other_anchor = anchor_root("0x"+"ab"*32, 1)
    with SessionLocal() as db:
        batch = db.get(MerkleBatch, batch_id); old_id = batch.chain_batch_id
        batch.chain_batch_id = other_anchor["chain_batch_id"]; db.commit()
    verify(target, reporter, "altered")
    with SessionLocal() as db:
        db.get(MerkleBatch, batch_id).chain_batch_id = old_id; db.commit()
    passed("5: substituted existing on-chain batch ID is altered")
    for variant in [raw[:-1], raw+b"x"]:
        replace_bytes(variant); verify(target, reporter, "altered")
    restore(); passed("6: truncated and appended files are altered")
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(raw)))
    writer.add_metadata({"/Title":"changed metadata"}); out=io.BytesIO(); writer.write(out)
    replace_bytes(out.getvalue()); verify(target, reporter, "altered"); restore()
    passed("7: re-saving PDF metadata is altered")
    # Operational errors are not evidence alteration findings.
    delete_encrypted_evidence(storage_key); verify(target, reporter, "error"); restore()
    store_encrypted_evidence(storage_key, encrypted[:-1]+bytes([encrypted[-1]^1]))
    verify(target, reporter, "error"); restore()
    passed("missing objects and unreadable AES-GCM ciphertext return audited error")
    for role in ["reporter", "investigator", "legal", "admin"]:
        user = users[role]
        verify(target, user, "verified")
        assert client.get(f"/evidence/{target}", headers=auth(user)).status_code == 200
        response = client.get(f"/evidence/{target}/proof", headers=auth(user)); assert response.status_code == 200
        assert response.json()["batch_id"] == str(batch_id)
        assert isinstance(response.json()["chain_batch_id"], str)
        expected = 403 if role == "reporter" else 200
        assert client.get(f"/batches/{batch_id}", headers=auth(user)).status_code == expected
    for suffix in ["", "/proof", "/verify"]:
        method = "POST" if suffix == "/verify" else "GET"
        assert client.request(method,f"/evidence/{target}{suffix}").status_code == 401
        assert client.request(method,f"/evidence/{target}{suffix}",headers=auth(users["other"])).status_code == 404
    passed("reporter ownership, privileged roles, unauthenticated and cross-case access rules")
    assert client.get(f"/evidence/{target}/file", headers=auth(users["other"])).status_code == 404
    assert client.get(f"/evidence/{target}/receipt", headers=auth(users["other"])).status_code == 404
    assert client.get("/audit", headers=auth(reporter)).status_code == 403
    for role in ["legal", "admin"]:
        audit_rows = client.get("/audit", headers=auth(users[role]))
        assert audit_rows.status_code == 200 and audit_rows.json()
    audit_check = client.get("/audit/verify", headers=auth(users["legal"]))
    assert audit_check.status_code == 200 and audit_check.json()["valid"] is True
    passed("authenticated file access, signed receipt verification, and role-protected audit API")
    admin_headers = auth(users["admin"])
    assert client.get("/admin/users", headers=admin_headers).status_code == 200
    self_disable = client.patch(f"/admin/users/{users['admin'].id}", headers=admin_headers, json={"is_active":False})
    assert self_disable.status_code == 409, self_disable.text
    disable_reporter = client.patch(f"/admin/users/{users['other'].id}", headers=admin_headers, json={"is_active":False})
    assert disable_reporter.status_code == 200 and disable_reporter.json()["is_active"] is False
    passed("admin user management protects the current/last administrator")
    timings=[]
    for number in range(10):
        evidence_id=upload(pdf_bytes(f"timing-{number}"))
        start=time.perf_counter(); anchor([evidence_id]); timings.append(time.perf_counter()-start)
        verify(evidence_id,reporter,"verified")
    assert max(timings)<60, timings
    passed("ten trigger-to-confirmation measurements below 60 seconds on local Hardhat")
    with SessionLocal() as db:
        audit=verify_audit_chain(db); assert audit["valid"],audit
    passed("audit chain remains valid after all verification and proof reads")
    result={"measured_at":datetime.now(timezone.utc).isoformat(),"network":"isolated Hardhat 31337",
            "all_ten_guide_cases_passed":False,"checks":checks,"outage_evidence_id":target,
            "timings_seconds":timings,"median_seconds":statistics.median(timings),"max_seconds":max(timings),
            "scope":"HTTP + PostgreSQL + encrypted object storage + actual chain; synthetic fixtures only"}
    RESULT.write_text(json.dumps(result,indent=2))
    print("READY: stop only the isolated test chain and run --outage",flush=True)

if __name__ == "__main__": main()
