
import hashlib
import io
import logging
import os
import secrets
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.access import can_access_case
from backend.database import SessionLocal, check_database_connection
from backend.login_limits import clear_email_attempts, consume_login_attempt
from backend.models import Case, Evidence, User
from backend.security import encrypt_evidence_stream
from backend.storage import delete_encrypted_evidence, get_s3_client, store_encrypted_evidence_fileobj
from backend.audit import append_audit_event
from backend.app.receipts import iso_utc, sign_receipt
from backend.app.api.reports import create_reports_router
from backend.app.api.analysis import create_analysis_router
from backend.app.api.cases import create_cases_router
from backend.app.api.audit import create_audit_router
from backend.app.api.users import create_users_router
from backend.app.api.complaints import create_complaints_router
from backend.app.ai.jobs import enqueue_analysis
from backend.app.ai.categories import clean_investigation_categories

app = FastAPI(
    title="DigitalWitness API",
    description="Backend for secure digital evidence preservation.",
    version="0.2.0",
)


def _error_code(status_code: int) -> str:
    return {
        400: "bad_request", 401: "authentication_required", 403: "forbidden",
        404: "not_found", 409: "conflict", 413: "payload_too_large",
        422: "validation_error", 429: "rate_limited", 503: "service_unavailable",
    }.get(status_code, "request_failed")


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    details = exc.detail if isinstance(exc.detail, (dict, list)) else {}
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"error": {"code": _error_code(exc.status_code), "message": message, "details": details}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    issues = [
        {"loc": list(error.get("loc", ())), "msg": str(error.get("msg", "Invalid value.")), "type": str(error.get("type", "validation_error"))}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed.", "details": {"issues": issues}}},
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "X-Report-SHA256", "X-Complaint-Packet-SHA256", "X-Complaint-Packet-Format"],
)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
if MAX_UPLOAD_MB < 1:
    raise RuntimeError("MAX_UPLOAD_MB must be a positive integer.")
MAX_FILE_SIZE = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".txt", ".json", ".mp3", ".wav", ".m4a", ".mp4", ".mov", ".webm"}
CANONICAL_MIME_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".pdf": "application/pdf", ".txt": "text/plain",
    ".json": "application/json", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".m4a": "audio/mp4", ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".webm": "video/webm",
}
bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)
DUMMY_PASSWORD_HASH = hash_password("digitalwitness-invalid-login-dummy-password")


def _file_signature_matches(data: bytes, extension: str) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if extension == ".pdf":
        return data.startswith(b"%PDF-")
    if extension in {".mp4", ".mov", ".m4a"}:
        return len(data) >= 12 and data[4:8] == b"ftyp"
    if extension == ".mp3":
        return data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
    if extension == ".wav":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if extension == ".webm":
        return data.startswith(b"\x1a\x45\xdf\xa3")
    if extension in {".txt", ".json"}:
        return bool(data)
    return False


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: DBSession,
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(credentials.credentials)
        user_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@app.get("/")
def home():
    return {"message": "Welcome to DigitalWitness"}


@app.get("/health")
def health_check():
    checks = {"database": "ok", "object_storage": "ok"}
    try:
        check_database_connection()
    except Exception:
        checks["database"] = "unavailable"
    try:
        get_s3_client().list_buckets()
    except Exception:
        checks["object_storage"] = "unavailable"
    healthy = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "healthy" if healthy else "unhealthy", "checks": checks},
    )


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(payload: RegisterRequest, request: Request, db: DBSession):
    email = str(payload.email).strip().lower()
    full_name = payload.full_name.strip()

    if not full_name:
        raise HTTPException(
            status_code=422,
            detail="Full name cannot be empty.",
        )

    existing_user = db.scalar(select(User).where(User.email == email))

    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(payload.password),
        role="reporter",
        is_active=True,
    )

    db.add(user)

    try:
        db.flush()
        append_audit_event(
            db, action="auth.register", target_type="user", actor_id=user.id,
            actor_role=user.role, target_id=str(user.id),
            ip=request.client.host if request.client else None,
        )
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        ) from None

    return user


class CaseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CaseResponse(BaseModel):
    id: UUID
    case_ref: str
    title: str
    description: str | None
    status: str


@app.post(
    "/cases",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    payload: CaseCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
):
    if current_user.role != "reporter":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only reporter accounts can open a case. Investigators review submitted reports.",
        )

    title = payload.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Case title cannot be empty.",
        )

    case = Case(
        case_ref=f"DW-{datetime.now(timezone.utc).year}-{secrets.token_hex(10).upper()}",
        title=title,
        description=payload.description,
        status="open",
        created_by=current_user.id,
    )

    db.add(case)
    db.flush()
    append_audit_event(
        db, action="case.create", target_type="case", actor_id=current_user.id,
        actor_role=current_user.role, target_id=str(case.id), case_id=case.id,
        ip=request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(case)

    return case

@app.post("/auth/login")
def login_user(payload: LoginRequest, request: Request, db: DBSession):
    email = str(payload.email).strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    retry_after = consume_login_attempt(email, ip_address)
    if retry_after is not None:
        append_audit_event(
            db, action="auth.login_limited", target_type="authentication",
            ip=ip_address, details={"retry_after_seconds": retry_after},
        )
        db.commit()
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(select(User).where(User.email == email))
    stored_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_matches = verify_password(payload.password, stored_hash)

    if user is None or not user.is_active or not password_matches:
        append_audit_event(
            db, action="auth.login_failure", target_type="authentication",
            actor_id=user.id if user else None, actor_role=user.role if user else None,
            ip=ip_address,
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_email_attempts(email)
    token = create_access_token(user.id, user.role)
    append_audit_event(
        db, action="auth.login_success", target_type="user", actor_id=user.id,
        actor_role=user.role, target_id=str(user.id), ip=ip_address,
    )
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(os.getenv("JWT_EXPIRE_MINUTES", "60")) * 60,
    }


@app.get("/auth/me", response_model=UserResponse)
@app.get("/me", response_model=UserResponse, include_in_schema=False)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@app.post("/evidence/upload", status_code=status.HTTP_201_CREATED)
def upload_evidence(
    case_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    investigation_categories: Annotated[list[str] | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "reporter":
        file.file.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only reporter accounts can submit evidence. Investigators review submitted files.",
        )

    try:
        selected_categories = clean_investigation_categories(investigation_categories)
    except ValueError as exc:
        file.file.close()
        raise HTTPException(status_code=422, detail=str(exc)) from None

    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or len(filename) > 255:
        file.file.close()
        raise HTTPException(
            status_code=400,
            detail="A valid filename of at most 255 characters is required.",
        )

    if extension not in ALLOWED_TYPES:
        file.file.close()
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload JPG, PNG, WEBP, PDF, TXT, JSON, MP3, WAV, M4A, MP4, MOV, or WEBM.",
        )

    case = db.get(Case, case_id)
    if case is None or not can_access_case(current_user, case):
        file.file.close()
        raise HTTPException(status_code=404, detail="Case not found.")

    sha256 = hashlib.sha256()
    size_bytes = 0
    header = bytearray()
    stored = False
    committed = False
    storage_key = f"cases/{case_id}/evidence/{secrets.token_hex(16)}"
    evidence_id = uuid4()
    uploaded_at = datetime.now(timezone.utc)
    digest = ""
    try:
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as original:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_UPLOAD_MB} MB.")
                if len(header) < 64:
                    header.extend(chunk[: 64 - len(header)])
                original.write(chunk)
                sha256.update(chunk)
            file.file.close()

            if size_bytes == 0:
                raise HTTPException(status_code=400, detail="Empty files cannot be uploaded.")
            if not _file_signature_matches(bytes(header), extension):
                raise HTTPException(status_code=400, detail="File contents do not match the selected file type.")
            if extension == ".txt":
                import codecs
                decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
                original.seek(0)
                try:
                    while chunk := original.read(1024 * 1024):
                        decoder.decode(chunk)
                    decoder.decode(b"", final=True)
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="Text evidence must be valid UTF-8.") from None
            elif extension == ".json":
                original.seek(0)
                try:
                    json.load(io.TextIOWrapper(original, encoding="utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise HTTPException(status_code=400, detail="JSON evidence must contain valid UTF-8 JSON.") from None
                finally:
                    # TextIOWrapper closes the underlying spool when released;
                    # reopen it before streaming encryption.
                    original.detach()
            digest = sha256.hexdigest()
            receipt_payload = {
                "receipt_id": str(evidence_id), "case_ref": case.case_ref,
                "case_id": str(case_id), "evidence_id": str(evidence_id),
                "filename": filename, "mime_type": CANONICAL_MIME_TYPES[extension],
                "size_bytes": size_bytes, "sha256": digest,
                "uploaded_at": iso_utc(uploaded_at), "status": "stored",
                "investigation_categories": selected_categories,
            }
            try:
                signature = sign_receipt(receipt_payload)
            except RuntimeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from None

            with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as encrypted:
                original.seek(0)
                nonce = encrypt_evidence_stream(original, encrypted)
                encrypted.seek(0)
                store_encrypted_evidence_fileobj(storage_key, encrypted)
                stored = True

            evidence = Evidence(
                id=evidence_id, case_id=case_id, uploader_id=current_user.id,
                original_filename=filename, mime_type=CANONICAL_MIME_TYPES[extension],
                size_bytes=size_bytes, sha256=digest, storage_key=storage_key,
                status="stored", analysis_status="pending", uploaded_at=uploaded_at,
                metadata_json={
                    "encryption": "AES-256-GCM", "nonce_bytes": len(nonce),
                    "investigation_categories": selected_categories,
                    "receipt_payload": receipt_payload,
                },
                receipt_signature=signature,
            )
            db.add(evidence)
            db.flush()
            enqueue_analysis(db, str(evidence.id))
            append_audit_event(
                db, action="evidence.upload", target_type="evidence",
                actor_id=current_user.id, actor_role=current_user.role,
                target_id=str(evidence.id), case_id=case_id,
                ip=request.client.host if request.client else None,
                details={"sha256": digest, "size_bytes": size_bytes, "mime_type": evidence.mime_type},
            )
            db.commit()
            committed = True
            db.refresh(evidence)
            return {**receipt_payload, "id": str(evidence.id), "receipt_signature": signature, "signature_valid": True}
    except Exception:
        file.file.close()
        if not committed:
            db.rollback()
        if stored and not committed:
            try:
                delete_encrypted_evidence(storage_key)
            except Exception:
                logger.exception("Failed to remove orphaned evidence object %s", storage_key)
        raise
    finally:
        file.file.close()


app.include_router(
    create_analysis_router(
        get_db_dependency=get_db,
        get_current_user_dependency=get_current_user,
    )
)

app.include_router(
    create_cases_router(
        get_db_dependency=get_db,
        get_current_user_dependency=get_current_user,
    )
)

app.include_router(
    create_reports_router(
        get_db_dependency=get_db,
        get_current_user_dependency=get_current_user,
    )
)

app.include_router(
    create_complaints_router(
        get_db_dependency=get_db,
        get_current_user_dependency=get_current_user,
    )
)


from backend.app.api.integrity import create_integrity_router

app.include_router(create_integrity_router(
    get_db_dependency=get_db, get_current_user_dependency=get_current_user,
))

app.include_router(create_audit_router(
    get_db_dependency=get_db, get_current_user_dependency=get_current_user,
))

app.include_router(create_users_router(
    get_db_dependency=get_db, get_current_user_dependency=get_current_user,
))
