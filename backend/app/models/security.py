from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, utcnow


class OwnershipTransfer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ownership_transfers"

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    from_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    to_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    to_email: Mapped[str] = mapped_column(String(320), nullable=False)
    to_organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending_recipient", nullable=False)
    recipient_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TheftAlert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "theft_alerts"

    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    matched_registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="new", nullable=False)
    investigation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SimilarityAnalysis(Base, UUIDMixin):
    __tablename__ = "similarity_analyses"

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    compared_registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    method: Mapped[str] = mapped_column(String(48), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Dispute(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "disputes"

    dispute_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    claimant_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    respondent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    earliest_registration_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DisputeEvidence(Base, UUIDMixin):
    __tablename__ = "dispute_evidence"

    dispute_id: Mapped[str] = mapped_column(String(36), ForeignKey("disputes.id"), index=True, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Notification(Base, UUIDMixin):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_logs"

    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    actor_ref: Mapped[str] = mapped_column(String(120), default="system", nullable=False)
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
