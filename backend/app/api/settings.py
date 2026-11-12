import secrets
import string
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user
from app.models import Organization, OrganizationInvitation, OrganizationMember, Registration, User, UserSession
from app.schemas.auth import validate_password_strength
from app.schemas.content import (
    OrganizationCreateRequest,
    OrganizationInviteAcceptRequest,
    OrganizationInviteRequest,
    OrganizationMemberCreateRequest,
    OrganizationSettingsRequest,
)
from app.security.crypto import random_url_token, utcnow
from app.security.passwords import hash_password
from app.security.rate_limit import member_limiter
from app.services.audit import append_audit
from app.services.notifications import notify

router = APIRouter(prefix="/settings", tags=["settings"])

MEMBER_ROLES = {"org_member", "org_admin"}


def _slugify(value: str) -> str:
    lowered = "".join(character if character.isalnum() else "-" for character in value.lower())
    slug = "-".join(part for part in lowered.split("-") if part)[:120]
    return f"{slug or 'organization'}-{secrets.token_hex(3)}"


def _ensure_organization(db: Session, user: User) -> Organization | None:
    if user.organization_id:
        return db.get(Organization, user.organization_id)
    if user.role != "org_admin":
        return None
    organization = Organization(
        name=f"{user.display_name} Organization",
        slug=_slugify(user.display_name),
        owner_id=user.id,
    )
    db.add(organization)
    db.flush()
    user.organization_id = organization.id
    member = OrganizationMember(
        organization_id=organization.id,
        user_id=user.id,
        role="org_admin",
        status="active",
    )
    db.add(member)
    db.commit()
    db.refresh(organization)
    return organization


def _generate_password(length: int = 16) -> str:
    rng = secrets.SystemRandom()
    required = [
        rng.choice(string.ascii_lowercase),
        rng.choice(string.ascii_uppercase),
        rng.choice(string.digits),
        rng.choice("!@#$%&*?"),
    ]
    body = [rng.choice(string.ascii_letters + string.digits) for _ in range(max(6, length - len(required)))]
    characters = required + body
    rng.shuffle(characters)
    candidate = "".join(characters)
    validate_password_strength(candidate)
    return candidate


def _managed_organization(db: Session, user: User) -> Organization:
    organization = _ensure_organization(db, user)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You do not belong to an organization")
    if organization.owner_id != user.id and user.role != "org_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an organization admin can manage members")
    return organization


def _member_payload(member: OrganizationMember, account: User) -> dict:
    return {
        "user_id": account.id,
        "display_name": account.display_name,
        "email": account.email,
        "role": member.role,
        "status": member.status,
        "created_at": account.created_at.isoformat(),
    }


def _invitation_out(invitation: OrganizationInvitation, organization: Organization | None = None) -> dict:
    return {
        "id": invitation.id,
        "organization_id": invitation.organization_id,
        "organization_name": organization.name if organization else None,
        "email": invitation.email,
        "display_name": invitation.display_name,
        "role": invitation.role,
        "status": invitation.status,
        "invite_token": invitation.invite_token,
        "invite_url": f"/join?code={invitation.invite_token}",
        "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
        "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
        "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None,
    }


@router.get("/organization")
def get_organization(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization = _ensure_organization(db, user)
    if not organization:
        return {"organization": None, "members": [], "can_manage": False}
    rows = db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == organization.id)
        .order_by(OrganizationMember.created_at.asc())
    ).all()
    invitations = db.execute(
        select(OrganizationInvitation)
        .where(
            OrganizationInvitation.organization_id == organization.id,
            OrganizationInvitation.status == "invited",
        )
        .order_by(OrganizationInvitation.created_at.desc())
    ).scalars().all()
    registration_count = db.execute(
        select(func.count()).select_from(Registration).where(Registration.organization_id == organization.id)
    ).scalar_one()
    return {
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "plan": organization.plan,
            "owner_id": organization.owner_id,
        },
        "members": [
            {
                "user_id": member.user_id,
                "display_name": account.display_name,
                "email": account.email,
                "role": member.role,
                "status": member.status,
                "is_owner": organization.owner_id == account.id,
                "is_you": account.id == user.id,
            }
            for member, account in rows
        ],
        "invitations": [_invitation_out(item, organization) for item in invitations],
        "registration_count": registration_count,
        "can_manage": user.role == "org_admin" or organization.owner_id == user.id,
    }


@router.post("/organization", status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create an organization for the signed-in account and make the user its admin."""
    if user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your account already belongs to an organization",
        )
    name = payload.name.strip()
    organization = Organization(
        name=name,
        slug=_slugify(name),
        owner_id=user.id,
    )
    db.add(organization)
    db.flush()
    user.organization_id = organization.id
    user.account_type = "organization"
    user.role = "org_admin"
    db.add(
        OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role="org_admin",
            status="active",
        )
    )
    append_audit(
        db,
        "organization_created",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="organization",
        entity_id=organization.id,
        metadata={"name": organization.name, "slug": organization.slug},
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    db.refresh(organization)
    return {
        "message": f"{organization.name} is ready. Invite your team from the organization page.",
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "plan": organization.plan,
            "owner_id": organization.owner_id,
        },
        "role": "org_admin",
    }


@router.get("/organization/invitations")
def list_organization_invitations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    organization = _ensure_organization(db, user)
    if not organization:
        return {"items": []}
    invitations = db.execute(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == organization.id)
        .order_by(OrganizationInvitation.created_at.desc())
    ).scalars().all()
    return {"items": [_invitation_out(item, organization) for item in invitations]}


@router.post("/organization/invitations", status_code=status.HTTP_201_CREATED)
def create_organization_invitation(
    payload: OrganizationInviteRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    organization = _managed_organization(db, user)
    allowed, retry_after = member_limiter.check(f"org-invite:{user.id}", 30, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many invitations. Retry in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    email = str(payload.email).strip().lower()
    already_member = db.execute(
        select(OrganizationMember)
        .join(User, OrganizationMember.user_id == User.id)
        .where(
            OrganizationMember.organization_id == organization.id,
            func.lower(User.email) == email,
        )
    ).scalar_one_or_none()
    if already_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That account is already a member of this organization",
        )
    pending = db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == organization.id,
            OrganizationInvitation.email == email,
            OrganizationInvitation.status == "invited",
        )
    ).scalar_one_or_none()
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An invitation for that email is already open",
        )

    invitation = OrganizationInvitation(
        organization_id=organization.id,
        email=email,
        display_name=payload.display_name,
        role=payload.role,
        invite_token=random_url_token(24),
        invited_by=user.id,
        status="invited",
        expires_at=utcnow() + timedelta(hours=payload.expires_in_hours),
    )
    db.add(invitation)
    db.flush()
    append_audit(
        db,
        "organization_invitation_created",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="organization",
        entity_id=organization.id,
        metadata={"email": email, "role": payload.role, "invitation_id": invitation.id},
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    invited_account = db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()
    if invited_account:
        notify(
            db,
            invited_account.id,
            "organization",
            f"Invitation to join {organization.name}",
            f"{user.display_name} invited you to join {organization.name}. Open the invite link to accept and get workspace access.",
            entity_type="organization",
            entity_id=organization.id,
        )
    db.commit()
    db.refresh(invitation)
    return {
        "message": f"Invitation created for {email}.",
        "invitation": _invitation_out(invitation, organization),
        "delivery": "In-app notification created for existing accounts. Email delivery is not configured in this environment.",
    }


@router.delete("/organization/invitations/{invitation_id}")
def revoke_organization_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    organization = _managed_organization(db, user)
    invitation = db.get(OrganizationInvitation, invitation_id)
    if not invitation or invitation.organization_id != organization.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    invitation.status = "revoked"
    append_audit(
        db,
        "organization_invitation_revoked",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="organization",
        entity_id=organization.id,
        metadata={"invitation_id": invitation.id, "email": invitation.email},
    )
    db.commit()
    return {"message": "Invitation revoked", "id": invitation.id}


@router.post("/organization/invitations/accept")
def accept_organization_invitation(
    payload: OrganizationInviteAcceptRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    token = (payload.token or "").strip()
    invitation = db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.invite_token == token,
            OrganizationInvitation.status == "invited",
        )
    ).scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation code not found or already used")
    if invitation.expires_at is not None:
        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=utcnow().tzinfo)
        if expires_at < utcnow():
            invitation.status = "expired"
            db.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="This invitation has expired. Ask for a new one.")

    organization = db.get(Organization, invitation.organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization no longer exists")

    if user.organization_id and user.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your account already belongs to another organization. Leave it first to join this one.",
        )

    member = db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == user.id,
        )
    ).scalar_one_or_none()
    if member is None:
        member = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=invitation.role,
            status="active",
        )
        db.add(member)
    else:
        member.status = "active"
        member.role = invitation.role

    if invitation.email.lower() != user.email.lower():
        invitation.email = user.email
    invitation.status = "accepted"
    invitation.accepted_at = utcnow()
    invitation.accepted_by = user.id
    user.organization_id = organization.id
    user.account_type = "organization"
    if user.role in {"creator", "verifier"}:
        user.role = "org_member" if invitation.role == "org_member" else user.role

    append_audit(
        db,
        "organization_invitation_accepted",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="organization",
        entity_id=organization.id,
        metadata={"invitation_id": invitation.id, "role": invitation.role},
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    notify(
        db,
        user.id,
        "organization",
        f"You joined {organization.name}",
        "You now have access to the shared organization workspace and its registrations.",
        entity_type="organization",
        entity_id=organization.id,
    )
    db.commit()
    return {
        "message": f"You joined {organization.name}",
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "plan": organization.plan,
            "owner_id": organization.owner_id,
        },
        "role": member.role,
    }


@router.get("/organization/registrations")
def organization_registrations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    organization = _ensure_organization(db, user)
    if not organization:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 0}
    query = select(Registration).where(Registration.organization_id == organization.id)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    items = db.execute(
        query.order_by(Registration.registered_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    owners = {
        owner.id: owner.display_name
        for owner in db.execute(select(User).where(User.id.in_({item.user_id for item in items}))).scalars()
    } if items else {}
    return {
        "items": [
            {
                "id": item.id,
                "registration_id": item.registration_id,
                "title": item.title,
                "description": item.description,
                "asset_type": item.asset_type,
                "file_name": item.file_name,
                "file_size": item.file_size,
                "mime_type": item.mime_type,
                "sha256": item.sha256,
                "commitment": item.commitment,
                "privacy": item.privacy,
                "status": item.status,
                "owner_id": item.user_id,
                "owner_name": owners.get(item.user_id),
                "registered_at": item.registered_at.isoformat() if item.registered_at else None,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("/organization/members", status_code=status.HTTP_201_CREATED)
def add_organization_member(
    payload: OrganizationMemberCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    organization = _managed_organization(db, user)
    allowed, retry_after = member_limiter.check(f"member-add:{user.id}", 30, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many member invitations. Please wait before adding another account.",
            headers={"Retry-After": str(retry_after)},
        )
    if payload.role not in MEMBER_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported organization member role")

    email = str(payload.email).strip().lower()
    existing = db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Ask the owner to use a different address.",
        )

    password = _generate_password()
    account = User(
        email=email,
        password_hash=hash_password(password),
        display_name=payload.display_name.strip(),
        account_type="organization",
        role="org_admin" if payload.role == "org_admin" else "creator",
        organization_id=organization.id,
        avatar_color=secrets.choice(["#171717", "#B7FF00", "#454545", "#888888", "#D0D0D0", "#EAEAEA"]),
    )
    db.add(account)
    db.flush()

    member = OrganizationMember(
        organization_id=organization.id,
        user_id=account.id,
        role=payload.role,
        status="active",
    )
    db.add(member)

    append_audit(
        db,
        "organization_member_added",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="user",
        entity_id=account.id,
        metadata={"email": email, "role": payload.role, "organization_id": organization.id},
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    notify(
        db,
        account.id,
        "organization",
        f"You were added to {organization.name}",
        f"{user.display_name} created your account. Sign in with the email and one-time password your administrator shared, then change the password in Settings.",
        entity_type="organization",
        entity_id=organization.id,
    )
    db.commit()
    db.refresh(account)
    db.refresh(member)

    return {
        "message": f"{account.display_name} can now sign in and join {organization.name}.",
        "member": _member_payload(member, account),
        "credentials": {
            "email": account.email,
            "password": password,
            "one_time": True,
            "note": "This password is shown once. Email delivery is not configured, so copy it now and share it over a secure channel.",
        },
    }


@router.post("/organization/members/{member_id}/password")
def reset_member_password(
    member_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    organization = _managed_organization(db, user)
    row = db.execute(
        select(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == organization.id, OrganizationMember.user_id == member_id)
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization member not found")
    member, account = row
    if account.id == organization.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The organization owner's password cannot be reset by another administrator")

    password = _generate_password()
    account.password_hash = hash_password(password)
    account.failed_login_count = 0
    account.locked_until = None
    sessions = db.execute(
        select(UserSession).where(UserSession.user_id == account.id, UserSession.revoked_at.is_(None))
    ).scalars()
    revoked = 0
    for session in sessions:
        session.revoked_at = utcnow()
        revoked += 1

    append_audit(
        db,
        "organization_member_password_reset",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="user",
        entity_id=account.id,
        metadata={"email": account.email, "sessions_revoked": revoked},
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    notify(
        db,
        account.id,
        "security",
        "Your password was reset by an organization admin",
        f"{user.display_name} generated a new password for your account. Every existing session was signed out.",
        entity_type="organization",
        entity_id=organization.id,
    )
    db.commit()

    return {
        "message": f"A new password was generated for {account.display_name}. Existing sessions were revoked.",
        "member": _member_payload(member, account),
        "credentials": {
            "email": account.email,
            "password": password,
            "one_time": True,
            "note": "This password is shown once. Copy it now and share it over a secure channel.",
        },
    }


@router.patch("/organization")
def update_organization(
    payload: OrganizationSettingsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    organization = _managed_organization(db, user)
    organization.name = payload.name
    append_audit(
        db,
        "organization_updated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="organization",
        entity_id=organization.id,
        metadata={"name": organization.name},
    )
    db.commit()
    return {"message": "Organization updated", "name": organization.name}


@router.get("/security")
def security_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session_count = db.execute(
        select(func.count())
        .select_from(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).scalar_one()
    return {
        "password_hashing": "Argon2id",
        "access_token_minutes": settings.access_token_minutes,
        "refresh_token_days": settings.refresh_token_days,
        "session_count": session_count,
        "passkeys": {"available": False, "reason": "Passkey enrollment is not configured in this deployment."},
        "mfa": {"available": False, "reason": "TOTP enrollment is not configured in this deployment."},
        "data_encryption_at_rest": True,
        "private_files_encrypted": True,
        "audit_chain_enabled": True,
    }
