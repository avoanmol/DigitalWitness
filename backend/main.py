
import hashlib
import os
from pathlib import Path
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
from backend.database import SessionLocal
from backend.models import Case,Evidence,User
from backend.security import encrypt_evidence
from backend.storage import store_encrypted_evidence
import secrets
import hmac
import hashlib
import base64
app = FastAPI(
    title="DigitalWitness API",
    description="Backend for secure digital evidence preservation.",
    version="0.2.0",
)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {".jpg", ".jpeg", ".png", ".pdf"}
bearer_scheme = HTTPBearer(auto_error=False)


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
    return {"status": "healthy"}


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(payload: RegisterRequest, db: DBSession):
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: DBSession,
):
    title = payload.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Case title cannot be empty.",
        )

    case = Case(
        case_ref=f"DW-{__import__('datetime').datetime.now().year}-{UUID(int=__import__('uuid').uuid4().int).hex[:8].upper()}",
        title=title,
        description=payload.description,
        status="open",
        created_by=current_user.id,
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return case

@app.post("/auth/login")
def login_user(payload: LoginRequest, db: DBSession):
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id, user.role)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(os.getenv("JWT_EXPIRE_MINUTES", "60")) * 60,
    }


@app.get("/auth/me", response_model=UserResponse)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@app.post("/evidence/upload", status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: UUID,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or len(filename) > 255:
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="A valid filename of at most 255 characters is required.",
        )

    if extension not in ALLOWED_TYPES:
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload JPG, PNG, or PDF.",
        )

    case = db.get(Case, case_id)
    if case is None:
        await file.close()
        raise HTTPException(status_code=404, detail="Case not found.")

    sha256 = hashlib.sha256()
    original_data = bytearray()

    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break

            original_data.extend(chunk)

            if len(original_data) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="File too large. Maximum size is 10 MB.",
                )

            sha256.update(chunk)
    finally:
        await file.close()

    original_bytes = bytes(original_data)
    encrypted_data, nonce = encrypt_evidence(original_bytes)

    storage_key = f"cases/{case_id}/evidence/{secrets.token_hex(16)}"
    object_data = nonce + encrypted_data

    try:
        store_encrypted_evidence(storage_key, object_data)

        receipt_key = os.getenv("RECEIPT_HMAC_KEY")
        if not receipt_key:
            raise RuntimeError("RECEIPT_HMAC_KEY is not configured.")

        digest = sha256.hexdigest()
        signature = hmac.new(
            receipt_key.encode("utf-8"),
            f"{case_id}:{current_user.id}:{storage_key}:{digest}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        evidence = Evidence(
            case_id=case_id,
            uploader_id=current_user.id,
            original_filename=filename,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=len(original_bytes),
            sha256=digest,
            storage_key=storage_key,
            status="stored",
            analysis_status="pending",
            metadata_json={
                "encryption": "AES-256-GCM",
                "nonce_bytes": len(nonce),
            },
            receipt_signature=signature,
        )

        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        return {
            "id": str(evidence.id),
            "case_id": str(evidence.case_id),
            "filename": evidence.original_filename,
            "size_bytes": evidence.size_bytes,
            "sha256": evidence.sha256,
            "status": evidence.status,
            "receipt_signature": evidence.receipt_signature,
        }

    except Exception:
        db.rollback()
        raise