from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OwnershipTransfer, Registration
from app.security.crypto import decrypt_text

PENDING_TRANSFER_STATUSES = ("pending_recipient", "recipient_accepted")


def registration_or_404(db, registration_id: str) -> Registration:
    registration = db.get(Registration, registration_id)
    if not registration:
        registration = db.query(Registration).filter(Registration.registration_id == registration_id).first()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    return registration


def is_registration_owner(user, registration) -> bool:
    return bool(user) and bool(getattr(user, "id", None)) and registration.user_id == user.id


def pending_transfer_for(db: Session, registration, user) -> OwnershipTransfer | None:
    """The incoming transfer for this user that has not been finalised yet.

    A recipient that has been proposed (or has accepted) a transfer can read the
    record and its file data while the current owner still holds ownership.
    """
    if not user or not getattr(user, "id", None):
        return None
    return db.execute(
        select(OwnershipTransfer)
        .where(
            OwnershipTransfer.registration_id == registration.id,
            OwnershipTransfer.to_user_id == user.id,
            OwnershipTransfer.status.in_(PENDING_TRANSFER_STATUSES),
        )
        .order_by(OwnershipTransfer.created_at.desc())
    ).scalars().first()


def can_access_registration(user, registration, db) -> bool:
    if is_registration_owner(user, registration):
        return True
    if registration.organization_id and user.organization_id == registration.organization_id:
        return True
    if getattr(registration, "team_project_id", None):
        from app.services.team_context import is_team_participant

        if is_team_participant(db, registration.team_project_id, user):
            return True
    if pending_transfer_for(db, registration, user) is not None:
        return True
    return False


def require_registration_access(user, registration, db, allow_public: bool = False) -> None:
    if can_access_registration(user, registration, db):
        return
    if allow_public and registration.privacy in {"public_fingerprint", "public"}:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this registration")


def require_registration_owner(user, registration, db) -> None:
    """Guard for owner-only actions such as transfers, versions, and deletion."""
    if is_registration_owner(user, registration):
        return
    if pending_transfer_for(db, registration, user) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ownership is still with the current owner. Only the recorded owner can perform this action.",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the recorded owner can perform this action",
    )


def secret_for(registration) -> tuple[int, int]:
    secret_int = int(decrypt_text(registration.secret_encrypted), 16)
    blinding_int = int(decrypt_text(registration.blinding_encrypted), 16)
    return secret_int, blinding_int


def decrypt_idea_description(idea) -> str:
    return decrypt_text(idea.description_encrypted)
