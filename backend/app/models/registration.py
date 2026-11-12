from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, utcnow


class Registration(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "registrations"
    __table_args__ = (
        Index("ix_registrations_sha256", "sha256"),
        Index("ix_registrations_user_status", "user_id", "status"),
        UniqueConstraint("registration_id", name="uq_registration_public_id"),
    )

    registration_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), index=True, nullable=True)
    team_project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("team_projects.id"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(40), default="document", nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), default="application/octet-stream", nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    commitment: Mapped[str] = mapped_column(String(160), nullable=False)
    poseidon_commitment: Mapped[str] = mapped_column(String(80), nullable=False)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    blinding_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    privacy: Mapped[str] = mapped_column(String(32), default="private", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="registered", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ledger_mode: Mapped[str] = mapped_column(String(32), default="simulation", nullable=False)
    creation_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)


class FileMetadata(Base, UUIDMixin):
    __tablename__ = "file_metadata"

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), unique=True, index=True, nullable=False
    )
    original_name: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    encrypted_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    perceptual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Upload(Base, UUIDMixin):
    __tablename__ = "uploads"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="initiated", nullable=False)
    final_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    per_chunk_sha256: Mapped[list | None] = mapped_column(JSON, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FileChunk(Base, UUIDMixin):
    __tablename__ = "file_chunks"
    __table_args__ = (UniqueConstraint("upload_id", "chunk_index", name="uq_upload_chunk"),)

    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("uploads.id"), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Commitment(Base, UUIDMixin):
    __tablename__ = "commitments"

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    scheme: Mapped[str] = mapped_column(String(80), nullable=False)
    commitment_hex: Mapped[str] = mapped_column(String(160), nullable=False)
    poseidon_hex: Mapped[str] = mapped_column(String(80), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ZkpChallenge(Base, UUIDMixin):
    __tablename__ = "zkp_challenges"

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    nonce: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), default="proof", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ZkpProof(Base, UUIDMixin):
    __tablename__ = "zkp_proofs"

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    challenge_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("zkp_challenges.id"), nullable=True)
    scheme: Mapped[str] = mapped_column(String(80), nullable=False)
    public_signals: Mapped[dict] = mapped_column(JSON, nullable=False)
    proof: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="generated", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VerificationRequest(Base, UUIDMixin):
    __tablename__ = "verification_requests"

    verification_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    creator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    challenge_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("zkp_challenges.id"), nullable=True)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    disclosure: Mapped[dict] = mapped_column(JSON, nullable=False)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    proof_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("zkp_proofs.id"), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LedgerTransaction(Base, UUIDMixin):
    __tablename__ = "ledger_transactions"
    __table_args__ = (Index("ix_ledger_type_entity", "tx_type", "entity_id"),)

    tx_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tx_type: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(24), default="simulation", nullable=False)
    network: Mapped[str] = mapped_column(String(80), default="AUTHENTIQ Local Ledger", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="confirmed", nullable=False)
    chain_tx_hash: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
