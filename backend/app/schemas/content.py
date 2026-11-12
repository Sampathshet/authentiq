from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.auth import StrictModel


class UploadInitiateRequest(StrictModel):
    filename: str = Field(min_length=1, max_length=300)
    size_bytes: int = Field(gt=0)
    mime_type: str = Field(default="application/octet-stream", max_length=160)
    total_chunks: int = Field(gt=0, le=10000)
    chunk_size: int = Field(gt=0, le=16 * 1024 * 1024)
    client_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, value: str) -> str:
        cleaned = value.replace("\\", "/").split("/")[-1].strip()
        if not cleaned or cleaned in {".", ".."}:
            raise ValueError("Invalid file name")
        return cleaned[:300]


class UploadOut(StrictModel):
    upload_id: str
    filename: str
    size_bytes: int
    total_chunks: int
    chunk_size: int
    uploaded_chunks: int
    status: str
    final_sha256: str | None = None


class RegistrationCreateRequest(StrictModel):
    upload_id: str
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    asset_type: Literal[
        "image", "document", "pdf", "source_code", "design", "research", "audio", "video", "ai_generated", "other"
    ] = "document"
    creation_timestamp: datetime | None = None
    privacy: Literal["private", "public_fingerprint", "public"] = "private"
    tags: list[str] | None = None
    team_id: str | None = Field(default=None, min_length=3, max_length=80)
    scope_to_organization: bool | None = None

    @field_validator("tags")
    @classmethod
    def limit_tags(cls, value):
        if value and len(value) > 12:
            raise ValueError("At most 12 tags are allowed")
        return value


class DuplicateCheckRequest(StrictModel):
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    perceptual_hash: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{16}$")


class FingerprintVerifyRequest(StrictModel):
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    fingerprint: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class ChallengeRequest(StrictModel):
    registration_id: str
    purpose: Literal["proof", "share", "anonymous"] = "proof"


class ProofGenerateRequest(StrictModel):
    registration_id: str
    challenge_id: str
    file_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class ProofVerifyRequest(StrictModel):
    registration_id: str
    nonce: str = Field(min_length=8, max_length=200)
    proof: dict
    public_signals: dict | None = None


class AnonymousChallengeRequest(StrictModel):
    registration_id: str = Field(min_length=3, max_length=80)
    file_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class AnonymousProofVerifyRequest(StrictModel):
    challenge_id: str = Field(min_length=1, max_length=64)
    proof: dict


class PublicFingerprintCheckRequest(StrictModel):
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class ShareCreateRequest(StrictModel):
    registration_id: str
    expires_in_hours: int = Field(default=72, ge=1, le=720)
    max_uses: int = Field(default=1, ge=1, le=100)
    message: str | None = Field(default=None, max_length=500)
    disclosure: dict = Field(default_factory=dict)


class PublicVerifyRequest(StrictModel):
    proof_package: dict | None = None
    proof: dict | None = None
    public_signals: dict | None = None


class VersionCreateRequest(StrictModel):
    registration_id: str
    upload_id: str
    change_description: str | None = Field(default=None, max_length=2000)


class IdeaCreateRequest(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=20000)
    privacy: Literal["private", "timestamp_only", "organization"] = "private"


class IdeaNotesUpdateRequest(StrictModel):
    notes: str = Field(min_length=1, max_length=10000)


class IdeaRevisionCreateRequest(StrictModel):
    notes: str = Field(min_length=1, max_length=10000)


class ProvenanceRecordRequest(StrictModel):
    registration_id: str
    declared_ai: bool
    model_name: str | None = Field(default=None, max_length=160)
    tool_name: str | None = Field(default=None, max_length=160)
    prompt_commitment: str | None = Field(default=None, max_length=300)
    human_contribution: str | None = Field(default=None, max_length=4000)
    editing_details: str | None = Field(default=None, max_length=4000)
    creation_date: datetime | None = None


class ProvenanceAnalyzeRequest(StrictModel):
    registration_id: str


class TeamCreateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class TeamInviteRequest(StrictModel):
    email: str = Field(min_length=5, max_length=320)
    role: Literal["contributor", "reviewer", "co_owner"] = "contributor"
    display_name: str | None = Field(default=None, max_length=120)


class TeamJoinRequest(StrictModel):
    token: str | None = Field(default=None, min_length=10)


class ContributionCreateRequest(StrictModel):
    description: str = Field(min_length=3, max_length=4000)
    file_reference: str | None = Field(default=None, max_length=300)


class AllocationItem(StrictModel):
    member_id: str
    percent: float = Field(ge=0, le=100)


class AllocationProposeRequest(StrictModel):
    allocations: list[AllocationItem]


class AllocationApproveRequest(StrictModel):
    allocation_ids: list[str]


class TransferCreateRequest(StrictModel):
    registration_id: str
    recipient_email: str = Field(min_length=5, max_length=320)
    to_organization_id: str | None = None
    reason: str | None = Field(default=None, max_length=2000)


class TransferDecisionRequest(StrictModel):
    reason: str | None = Field(default=None, max_length=2000)


class DisputeCreateRequest(StrictModel):
    registration_id: str
    reason: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20, max_length=8000)


class DisputeStatusRequest(StrictModel):
    status: Literal["under_review", "evidence_requested", "resolved", "rejected"]
    resolution: str | None = Field(default=None, max_length=4000)


class AlertStatusRequest(StrictModel):
    status: Literal["under_review", "resolved", "dismissed"]
    investigation_notes: str | None = Field(default=None, max_length=4000)


class NotificationReadRequest(StrictModel):
    ids: list[str] | None = None


class OrganizationSettingsRequest(StrictModel):
    name: str = Field(min_length=2, max_length=160)


class OrganizationCreateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=160)


class OrganizationMemberCreateRequest(StrictModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: Literal["org_member", "org_admin"] = "org_member"


class OrganizationInviteRequest(StrictModel):
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=120)
    role: Literal["org_member", "org_admin"] = "org_member"
    expires_in_hours: int = Field(default=168, ge=1, le=8760)


class OrganizationInviteAcceptRequest(StrictModel):
    token: str = Field(min_length=8, max_length=200)


class AdminUserUpdateRequest(StrictModel):
    role: Literal["creator", "verifier", "org_admin", "org_member", "site_admin"] | None = None
    is_active: bool | None = None
    organization_id: str | None = Field(default=None, max_length=64)
    clear_organization: bool = False


class AdminDisputeUpdateRequest(StrictModel):
    status: Literal["open", "under_review", "evidence_requested", "resolved"] | None = None
    resolution: str | None = Field(default=None, max_length=4000)


class EvidenceCreateRequest(StrictModel):
    description: str | None = Field(default=None, max_length=2000)
