from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, utcnow


class Idea(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ideas"
    __table_args__ = (UniqueConstraint("idea_ref", name="uq_idea_ref"),)

    idea_ref: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    commitment: Mapped[str] = mapped_column(String(80), nullable=False)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    privacy: Mapped[str] = mapped_column(String(32), default="private", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="protected", nullable=False)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ledger_mode: Mapped[str] = mapped_column(String(32), default="simulation", nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IdeaRevision(Base, UUIDMixin):
    __tablename__ = "idea_revisions"

    idea_id: Mapped[str] = mapped_column(String(36), ForeignKey("ideas.id"), index=True, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    notes_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    commitment: Mapped[str] = mapped_column(String(80), nullable=False)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CreativeVersion(Base, UUIDMixin):
    __tablename__ = "creative_versions"
    __table_args__ = (UniqueConstraint("registration_id", "version_no", name="uq_registration_version"),)

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    change_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contributor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("creative_versions.id"), nullable=True)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AIProvenance(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_provenance"

    registration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("registrations.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    declared_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    prompt_commitment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    human_contribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    editing_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    creation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
