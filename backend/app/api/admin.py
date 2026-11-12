"""Website-wide administration console.

Everything here is guarded by the ``site_admin`` role, so it sits above the
organization and workspace roles: the site administrator can control accounts,
disputes, organizations, teams, registrations, and the audit trail for the
whole deployment.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_site_admin
from app.ledger import ledger_service
from app.models import (
    AuditLog,
    Dispute,
    Idea,
    LedgerTransaction,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    Registration,
    TeamProject,
    TheftAlert,
    User,
    UserSession,
    ZkpProof,
)
from app.schemas.content import AdminDisputeUpdateRequest, AdminUserUpdateRequest
from app.security.crypto import utcnow
from app.services.audit import append_audit
from app.services.notifications import notify
from app.services.serializers import audit_out, dispute_out

router = APIRouter(prefix="/admin", tags=["site administration"])


def _count(db: Session, model, *conditions) -> int:
    query = select(func.count()).select_from(model)
    if conditions:
        query = query.where(*conditions)
    return db.execute(query).scalar_one()


@router.get("/overview")
def overview(db: Session = Depends(get_db), admin: User = Depends(require_site_admin)):
    ledger_status = ledger_service.status()
    storage = db.execute(
        select(func.coalesce(func.sum(Registration.file_size), 0))
    ).scalar_one()
    recent_users = db.execute(select(User).order_by(User.created_at.desc()).limit(6)).scalars().all()
    recent_disputes = db.execute(select(Dispute).order_by(Dispute.created_at.desc()).limit(6)).scalars().all()
    recent_audit = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(12)).scalars().all()
    return {
        "stats": {
            "users": _count(db, User),
            "active_users": _count(db, User, User.is_active.is_(True)),
            "suspended_users": _count(db, User, User.is_active.is_(False)),
            "site_admins": _count(db, User, User.role == "site_admin"),
            "organizations": _count(db, Organization),
            "teams": _count(db, TeamProject),
            "registrations": _count(db, Registration),
            "organization_registrations": _count(db, Registration, Registration.organization_id.isnot(None)),
            "ideas": _count(db, Idea),
            "disputes": _count(db, Dispute),
            "open_disputes": _count(db, Dispute, Dispute.status.in_(["open", "under_review", "evidence_requested"])),
            "resolved_disputes": _count(db, Dispute, Dispute.status == "resolved"),
            "alerts": _count(db, TheftAlert),
            "open_alerts": _count(db, TheftAlert, TheftAlert.status.in_(["new", "under_review"])),
            "ledger_transactions": _count(db, LedgerTransaction),
            "verified_proofs": _count(db, ZkpProof, ZkpProof.status == "verified"),
            "pending_org_invitations": _count(db, OrganizationInvitation, OrganizationInvitation.status == "invited"),
            "stored_bytes": int(storage or 0),
        },
        "ledger": ledger_status,
        "recent_users": [user_out(admin_row) for admin_row in recent_users],
        "recent_disputes": [dispute_out(item) for item in recent_disputes],
        "recent_audit": [audit_out(item) for item in recent_audit],
    }


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "account_type": user.account_type,
        "organization_id": user.organization_id,
        "is_active": user.is_active,
        "is_demo": user.is_demo,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.get("/users")
def list_users(
    q: str | None = Query(default=None, max_length=200),
    role: str | None = None,
    organization_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_site_admin),
):
    query = select(User)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(User.email.ilike(pattern), User.display_name.ilike(pattern)))
    if role:
        query = query.where(User.role == role)
    if organization_id:
        query = query.where(User.organization_id == organization_id)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    users = db.execute(
        query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    counts = {
        user.id: db.execute(
            select(func.count()).select_from(Registration).where(Registration.user_id == user.id)
        ).scalar_one()
        for user in users
    }
    return {
        "items": [{**user_out(user), "registrations": counts.get(user.id, 0)} for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_site_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="You cannot suspend your own account")

    changes: dict[str, object] = {}
    if payload.role and payload.role != user.role:
        user.role = payload.role
        changes["role"] = payload.role
    if payload.is_active is not None and payload.is_active != user.is_active:
        user.is_active = payload.is_active
        changes["is_active"] = payload.is_active
        if not payload.is_active:
            for session in db.execute(
                select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            ).scalars():
                session.revoked_at = utcnow()
            changes["sessions_revoked"] = True
    if payload.clear_organization and user.organization_id:
        for member in db.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        ).scalars():
            member.status = "removed"
        user.organization_id = None
        changes["organization_cleared"] = True
    elif payload.organization_id and payload.organization_id != user.organization_id:
        organization = db.get(Organization, payload.organization_id)
        if not organization:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        user.organization_id = organization.id
        member = db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == user.id,
            )
        ).scalar_one_or_none()
        if not member:
            db.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=user.id,
                    role="org_member",
                    status="active",
                )
            )
        changes["organization_id"] = organization.id

    append_audit(
        db,
        "site_admin_user_updated",
        actor_id=admin.id,
        actor_ref=admin.email,
        entity_type="user",
        entity_id=user.id,
        metadata=changes,
    )
    db.commit()
    return {"message": "User updated", "user": user_out(user), "changes": changes}


@router.get("/disputes")
def list_disputes(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_site_admin),
):
    query = select(Dispute)
    if status_filter:
        query = query.where(Dispute.status == status_filter)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    disputes = db.execute(
        query.order_by(Dispute.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    names = {}
    ids = {item.claimant_id for item in disputes} | {item.respondent_id for item in disputes if item.respondent_id}
    if ids:
        for account in db.execute(select(User).where(User.id.in_(ids))).scalars():
            names[account.id] = account.display_name
    registrations = {
        item.id: item
        for item in db.execute(
            select(Registration).where(Registration.id.in_({item.registration_id for item in disputes}))
        ).scalars()
    } if disputes else {}
    return {
        "items": [
            {
                **dispute_out(dispute, registrations.get(dispute.registration_id)),
                "claimant_name": names.get(dispute.claimant_id),
                "respondent_name": names.get(dispute.respondent_id) if dispute.respondent_id else None,
            }
            for dispute in disputes
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.patch("/disputes/{dispute_id}")
def update_dispute(
    dispute_id: str,
    payload: AdminDisputeUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_site_admin),
):
    dispute = db.get(Dispute, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    if payload.status:
        if payload.status in {"resolved"} and not (payload.resolution or dispute.resolution):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A resolution summary is required to resolve a dispute",
            )
        dispute.status = payload.status
        if payload.status == "resolved":
            dispute.resolved_at = utcnow()
            registration = db.get(Registration, dispute.registration_id)
            if registration:
                registration.status = "verified"
    if payload.resolution is not None:
        dispute.resolution = payload.resolution
    for recipient in (dispute.claimant_id, dispute.respondent_id):
        if recipient:
            notify(
                db,
                recipient,
                "dispute",
                "Dispute status changed by site administration",
                f"Dispute {dispute.dispute_ref} is now {dispute.status.replace('_', ' ')}.",
                "dispute",
                dispute.id,
            )
    append_audit(
        db,
        "site_admin_dispute_updated",
        actor_id=admin.id,
        actor_ref=admin.email,
        entity_type="dispute",
        entity_id=dispute.dispute_ref,
        metadata={"status": dispute.status},
    )
    db.commit()
    return {"message": "Dispute updated", "status": dispute.status, "resolution": dispute.resolution}


@router.get("/organizations")
def list_organizations(db: Session = Depends(get_db), admin: User = Depends(require_site_admin)):
    organizations = db.execute(select(Organization).order_by(Organization.created_at.desc())).scalars().all()
    payload = []
    for organization in organizations:
        members = _count(db, OrganizationMember, OrganizationMember.organization_id == organization.id)
        active = _count(
            db,
            OrganizationMember,
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.status == "active",
        )
        registrations = _count(
            db, Registration, Registration.organization_id == organization.id
        )
        invitations = _count(
            db,
            OrganizationInvitation,
            OrganizationInvitation.organization_id == organization.id,
            OrganizationInvitation.status == "invited",
        )
        owner = db.get(User, organization.owner_id)
        payload.append(
            {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug,
                "plan": organization.plan,
                "owner_id": organization.owner_id,
                "owner_name": owner.display_name if owner else None,
                "members": members,
                "active_members": active,
                "registrations": registrations,
                "pending_invitations": invitations,
                "created_at": organization.created_at.isoformat() if organization.created_at else None,
            }
        )
    return {"items": payload, "total": len(payload)}


@router.get("/registrations")
def list_registrations(
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_site_admin),
):
    query = select(Registration)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Registration.title.ilike(pattern),
                Registration.registration_id.ilike(pattern),
                Registration.sha256.ilike(pattern),
            )
        )
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    registrations = db.execute(
        query.order_by(Registration.registered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    owners = {
        owner.id: owner.display_name
        for owner in db.execute(
            select(User).where(User.id.in_({item.user_id for item in registrations}))
        ).scalars()
    } if registrations else {}
    return {
        "items": [
            {
                "id": item.id,
                "registration_id": item.registration_id,
                "title": item.title,
                "owner_id": item.user_id,
                "owner_name": owners.get(item.user_id),
                "organization_id": item.organization_id,
                "asset_type": item.asset_type,
                "privacy": item.privacy,
                "status": item.status,
                "sha256": item.sha256,
                "file_size": item.file_size,
                "registered_at": item.registered_at.isoformat() if item.registered_at else None,
            }
            for item in registrations
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/teams")
def list_teams(db: Session = Depends(get_db), admin: User = Depends(require_site_admin)):
    teams = db.execute(select(TeamProject).order_by(TeamProject.created_at.desc())).scalars().all()
    payload = []
    for team in teams:
        owner = db.get(User, team.owner_id)
        payload.append(
            {
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "owner_id": team.owner_id,
                "owner_name": owner.display_name if owner else None,
                "organization_id": team.organization_id,
                "status": team.status,
                "created_at": team.created_at.isoformat() if team.created_at else None,
            }
        )
    return {"items": payload, "total": len(payload)}


@router.get("/audit")
def audit_trail(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_site_admin),
):
    total = db.execute(select(func.count()).select_from(AuditLog)).scalar_one()
    entries = db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "items": [audit_out(entry) for entry in entries],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }
