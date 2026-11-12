from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, utcnow


class TeamProject(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "team_projects"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    ledger_tx_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TeamMember(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("project_id", "email", name="uq_team_member_email"),)

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("team_projects.id"), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="contributor", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="invited", nullable=False)
    invite_token: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    contribution_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ownership_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    invited_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContributionRecord(Base, UUIDMixin):
    __tablename__ = "contribution_records"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("team_projects.id"), index=True, nullable=False)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("team_members.id"), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    file_reference: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="submitted", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OwnershipAllocation(Base, UUIDMixin):
    __tablename__ = "ownership_allocations"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("team_projects.id"), index=True, nullable=False)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("team_members.id"), index=True, nullable=False)
    percent: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="proposed", nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    approvals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
