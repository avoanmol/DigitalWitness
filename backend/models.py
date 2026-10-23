
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    Numeric,
    Text,
    text,
    UniqueConstraint,
    Float,
    Identity

)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="reporter"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('reporter', 'investigator', 'legal', 'admin')",
            name="ck_users_role",
        ),
    )


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_ref: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    incident_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="open"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'under_review', 'closed')",
            name="ck_cases_status",
        ),
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(
        String(512), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="received"
    )
    analysis_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    receipt_signature: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "size_bytes > 0",
            name="ck_evidence_size_positive",
        ),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_sha256_format",
        ),
        CheckConstraint(
            "status IN ('received', 'stored', 'anchored', 'failed')",
            name="ck_evidence_status",
        ),
        CheckConstraint(
            "analysis_status IN ('pending', 'running', 'done', 'failed', 'skipped')",
            name="ck_evidence_analysis_status",
        ),
        Index("ix_evidence_case_id", "case_id"),
        Index("ix_evidence_status", "status"),
    )



class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    seq: Mapped[int] = mapped_column(
        BigInteger, Identity(), unique=True, nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_role: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    target_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    target_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=True,
    )
    ip: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    prev_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    entry_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "prev_hash ~ '^[0-9a-f]{64}$'",
            name="ck_audit_prev_hash_format",
        ),
        CheckConstraint(
            "entry_hash ~ '^[0-9a-f]{64}$'",
            name="ck_audit_entry_hash_format",
        ),
        Index("ix_audit_case_seq", "case_id", "seq"),
    )



class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed')",
            name="ck_jobs_status",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_jobs_attempts_nonnegative",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_jobs_max_attempts_positive",
        ),
        Index("ix_jobs_status_run_after", "status", "run_after"),
    )



class MerkleBatch(Base):
    __tablename__ = "merkle_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chain_batch_id: Mapped[int | None] = mapped_column(
        Numeric(78, 0), nullable=True
    )
    root_hash: Mapped[str] = mapped_column(
        String(66), nullable=False
    )
    leaf_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    tx_hash: Mapped[str | None] = mapped_column(
        String(66), nullable=True
    )
    chain_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=80002
    )
    block_number: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="building"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    anchored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('building', 'submitted', 'confirmed', 'failed')",
            name="ck_merkle_batches_status",
        ),
        CheckConstraint(
            "leaf_count BETWEEN 1 AND 4294967295",
            name="ck_merkle_batches_leaf_count",
        ),
        Index(
            "ix_merkle_batches_status_created",
            "status",
            "created_at",
        ),
        Index(
            "uq_merkle_batches_chain_batch",
            "chain_id",
            "chain_batch_id",
            unique=True,
            postgresql_where=text("chain_batch_id IS NOT NULL"),
        ),
    )


class MerkleProof(Base):
    __tablename__ = "merkle_proofs"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merkle_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    leaf_index: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    leaf_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    proof: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    __table_args__ = (
        CheckConstraint(
            "leaf_index >= 0",
            name="ck_merkle_proofs_leaf_index",
        ),
        CheckConstraint(
            "leaf_hash ~ '^[0-9a-f]{64}$'",
            name="ck_merkle_proofs_leaf_hash",
        ),
        UniqueConstraint(
            "batch_id",
            "leaf_index",
            name="uq_merkle_proofs_batch_leaf",
        ),
    )


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    result: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    recomputed_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    expected_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    computed_root: Mapped[str | None] = mapped_column(
        String(66), nullable=True
    )
    onchain_root: Mapped[str | None] = mapped_column(
        String(66), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "result IN ('verified', 'altered', 'pending', 'error')",
            name="ck_verifications_result",
        ),
        Index(
            "ix_verifications_evidence_checked",
            "evidence_id",
            "checked_at",
        ),
    )



class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    raw_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalised_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    source_span: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "type IN ('handle', 'phone', 'email', 'url')",
            name="ck_entities_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_entities_confidence",
        ),
        Index("ix_entities_type_normalised", "type", "normalised_value"),
    )


class ThreatFlag(Base):
    __tablename__ = "threat_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="RESTRICT"),
        nullable=False,
    )
    threat_class: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_threat_flags_severity",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'confirmed', 'rejected')",
            name="ck_threat_flags_review_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_threat_flags_confidence",
        ),
        Index("ix_threat_flags_review_severity", "review_status", "severity"),
    )


class CaseLink(Base):
    __tablename__ = "case_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shared_entities: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="suggested"
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "case_a_id < case_b_id",
            name="ck_case_links_order",
        ),
        CheckConstraint(
            "status IN ('suggested', 'confirmed', 'rejected')",
            name="ck_case_links_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_case_links_confidence",
        ),
        UniqueConstraint(
            "case_a_id", "case_b_id", name="uq_case_links_case_pair"
        ),
    )
