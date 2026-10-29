"""Authenticated evidence reads and integrity verification routes."""
import hashlib
import hmac
import os
from pathlib import PurePath
from urllib.parse import quote
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from backend.access import can_access_case
from backend.audit import append_audit_event
from backend.models import Case, Evidence, MerkleBatch
from backend.app.integrity.service import batch_fields, linked_batch, utc, verify_and_record
from backend.audit import append_audit_event
from backend.security import decrypt_evidence
from backend.storage import get_encrypted_evidence
from backend.app.receipts import iso_utc, verify_receipt

READ_ROLES = {"reporter", "investigator", "legal", "admin"}
EXPLORERS = {80002: "https://amoy.polygonscan.com/tx/", 137: "https://polygonscan.com/tx/"}


def create_integrity_router(*, get_db_dependency, get_current_user_dependency):
    router = APIRouter(tags=["integrity"])

    def permitted_evidence(db, evidence_id, user):
        if user.role not in READ_ROLES:
            raise HTTPException(403, "This role cannot read evidence.")
        evidence = db.get(Evidence, evidence_id)
        case = db.get(Case, evidence.case_id) if evidence else None
        # Do not reveal whether another reporter's evidence exists.
        if not evidence or not case or not can_access_case(user, case):
            raise HTTPException(404, "Evidence not found.")
        return evidence

    @router.get("/evidence/{evidence_id}")
    def metadata(evidence_id: UUID, request: Request, response: Response,
                 db=Depends(get_db_dependency), user=Depends(get_current_user_dependency)):
        from backend.app.api.cases import _serialize_evidence
        evidence = permitted_evidence(db, evidence_id, user)
        append_audit_event(db, action="evidence.metadata.read", target_type="evidence",
                           target_id=str(evidence.id), case_id=evidence.case_id,
                           actor_id=user.id, actor_role=user.role,
                           ip=request.client.host if request.client else None)
        db.commit()
        response.headers["Cache-Control"] = "no-store"
        return _serialize_evidence(db, [evidence])[0]

    @router.get("/evidence/{evidence_id}/file")
    def evidence_file(evidence_id: UUID, request: Request,
                      db=Depends(get_db_dependency), user=Depends(get_current_user_dependency)):
        evidence = permitted_evidence(db, evidence_id, user)
        try:
            encrypted = get_encrypted_evidence(evidence.storage_key)
            if len(encrypted) < 13:
                raise ValueError("Encrypted evidence object is incomplete.")
            original = decrypt_evidence(encrypted[12:], encrypted[:12])
        except Exception:
            append_audit_event(db, action="evidence.file.read_failed", target_type="evidence",
                               target_id=str(evidence.id), case_id=evidence.case_id,
                               actor_id=user.id, actor_role=user.role,
                               ip=request.client.host if request.client else None)
            db.commit()
            raise HTTPException(status_code=503, detail="Evidence file is temporarily unavailable.") from None
        append_audit_event(db, action="evidence.file.read", target_type="evidence",
                           target_id=str(evidence.id), case_id=evidence.case_id,
                           actor_id=user.id, actor_role=user.role,
                           ip=request.client.host if request.client else None,
                           details={"size_bytes": len(original)})
        db.commit()
        safe_name = PurePath(evidence.original_filename.replace("\\", "/")).name
        return Response(
            content=original,
            media_type=evidence.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(safe_name, safe='')}",
                "Content-Length": str(len(original)),
                "Cache-Control": "no-store, private",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @router.get("/evidence/{evidence_id}/receipt")
    def receipt(evidence_id: UUID, request: Request, response: Response,
                db=Depends(get_db_dependency), user=Depends(get_current_user_dependency)):
        evidence = permitted_evidence(db, evidence_id, user)
        case = db.get(Case, evidence.case_id)
        saved_payload = (evidence.metadata_json or {}).get("receipt_payload")
        if isinstance(saved_payload, dict):
            payload = saved_payload
            signature_valid = verify_receipt(payload, evidence.receipt_signature or "")
        else:
            # Existing local uploads used a compact pre-v1 signature. Preserve
            # their receipts while new uploads use the canonical payload below.
            payload = {
                "receipt_id": str(evidence.id), "case_ref": case.case_ref,
                "case_id": str(evidence.case_id), "evidence_id": str(evidence.id),
                "filename": evidence.original_filename, "mime_type": evidence.mime_type,
                "size_bytes": evidence.size_bytes, "sha256": evidence.sha256,
                "uploaded_at": iso_utc(evidence.uploaded_at), "status": evidence.status,
                "investigation_categories": (evidence.metadata_json or {}).get("investigation_categories", []),
            }
            key = os.getenv("RECEIPT_HMAC_KEY", "").encode("utf-8")
            legacy_message = f"{evidence.case_id}:{evidence.uploader_id}:{evidence.storage_key}:{evidence.sha256}".encode("utf-8")
            legacy_signature = hmac.new(key, legacy_message, hashlib.sha256).hexdigest() if key else ""
            signature_valid = hmac.compare_digest(legacy_signature, evidence.receipt_signature or "")
        append_audit_event(db, action="evidence.receipt.read", target_type="evidence",
                           target_id=str(evidence.id), case_id=evidence.case_id,
                           actor_id=user.id, actor_role=user.role,
                           ip=request.client.host if request.client else None,
                           details={"signature_valid": signature_valid})
        db.commit()
        response.headers["Cache-Control"] = "no-store"
        return {**payload, "signature": evidence.receipt_signature or "", "signature_valid": signature_valid}

    @router.post("/evidence/{evidence_id}/verify")
    def verify(evidence_id: UUID, request: Request,
               db=Depends(get_db_dependency), user=Depends(get_current_user_dependency)):
        evidence = permitted_evidence(db, evidence_id, user)
        return verify_and_record(db, evidence, user, request.client.host if request.client else None)

    @router.get("/evidence/{evidence_id}/proof")
    def proof(evidence_id: UUID, request: Request,
              db=Depends(get_db_dependency), user=Depends(get_current_user_dependency)):
        evidence = permitted_evidence(db, evidence_id, user)
        saved, batch = linked_batch(db, evidence.id)
        ready = bool(saved and batch and batch.status == "confirmed")
        state = "confirmed" if ready else ("error" if evidence.status == "anchored" else "pending")
        explorer = EXPLORERS.get(batch.chain_id) if batch else None
        response = {
            "evidence_id": str(evidence.id), **batch_fields(batch), "status": state,
            "leaf_index": saved.leaf_index if ready else None,
            "leaf_hash": saved.leaf_hash if ready else None,
            "proof": saved.proof if ready else None,
            "root": batch.root_hash if ready else None,
            "leaf_count": batch.leaf_count if ready else None,
            "explorer_url": explorer + batch.tx_hash if explorer and batch.tx_hash else None,
        }
        append_audit_event(db, action="evidence.proof.read", target_type="evidence",
                           target_id=str(evidence.id), case_id=evidence.case_id,
                           actor_id=user.id, actor_role=user.role,
                           ip=request.client.host if request.client else None,
                           details={"status": state, "batch_id": response["batch_id"]})
        db.commit()
        return response

    @router.get("/batches/{batch_id}")
    def batch(batch_id: UUID, db=Depends(get_db_dependency), user=Depends(get_current_user_dependency)):
        if user.role not in {"investigator", "legal", "admin"}:
            raise HTTPException(403, "This role cannot read batches.")
        saved = db.get(MerkleBatch, batch_id)
        if saved is None:
            raise HTTPException(404, "Batch not found.")
        return {"id": str(saved.id), **batch_fields(saved), "root_hash": saved.root_hash,
                "leaf_count": saved.leaf_count, "block_number": saved.block_number,
                "status": saved.status, "created_at": utc(saved.created_at),
                "anchored_at": utc(saved.anchored_at)}

    return router
