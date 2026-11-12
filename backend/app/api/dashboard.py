from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    AuditLog,
    CreativeVersion,
    Dispute,
    Idea,
    LedgerTransaction,
    Notification,
    OwnershipTransfer,
    Registration,
    TeamMember,
    TeamProject,
    TheftAlert,
    User,
    VerificationRequest,
    ZkpProof,
)
from app.ledger import ledger_service
from app.security.crypto import utcnow
from app.services.serializers import (
    alert_out,
    audit_out,
    ledger_out,
    notification_out,
    registration_out,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _registration_scope(user: User):
    if user.organization_id:
        return or_(Registration.user_id == user.id, Registration.organization_id == user.organization_id)
    return Registration.user_id == user.id


def _pending_registration_ids(db: Session, user: User) -> set[str]:
    rows = db.execute(
        select(OwnershipTransfer.registration_id).where(
            OwnershipTransfer.to_user_id == user.id,
            OwnershipTransfer.status.in_(["pending_recipient", "recipient_accepted"]),
        )
    ).scalars().all()
    return set(rows)


def _scoped_registrations(db: Session, user: User):
    """Owned records plus records whose ownership is being handed over to the user."""
    owned = list(db.execute(select(Registration).where(_registration_scope(user))).scalars().all())
    pending_ids = _pending_registration_ids(db, user)
    if not pending_ids:
        return owned, pending_ids
    incoming = list(
        db.execute(select(Registration).where(Registration.id.in_(pending_ids))).scalars().all()
    )
    known = {item.id for item in owned}
    return owned + [item for item in incoming if item.id not in known], pending_ids


def _team_ids(db: Session, user: User) -> list[str]:
    ids = set(
        db.execute(select(TeamMember.project_id).where(TeamMember.user_id == user.id)).scalars().all()
    )
    ids |= set(db.execute(select(TeamProject.id).where(TeamProject.owner_id == user.id)).scalars().all())
    return list(ids)


def _entity_ids(db: Session, user: User) -> list[str]:
    registrations = db.execute(select(Registration).where(_registration_scope(user))).scalars().all()
    ideas = db.execute(select(Idea).where(Idea.user_id == user.id)).scalars().all()
    teams = _team_ids(db, user)
    transfers = db.execute(
        select(OwnershipTransfer.id).where(or_(OwnershipTransfer.from_user_id == user.id, OwnershipTransfer.to_user_id == user.id))
    ).scalars().all()
    disputes = db.execute(
        select(Dispute.dispute_ref).where(or_(Dispute.claimant_id == user.id, Dispute.respondent_id == user.id))
    ).scalars().all()
    shares = db.execute(select(VerificationRequest.verification_id).where(VerificationRequest.creator_id == user.id)).scalars().all()
    return [item.registration_id for item in registrations] + [item.idea_ref for item in ideas] + teams + list(transfers) + list(disputes) + list(shares)


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registrations, pending_ids = _scoped_registrations(db, user)
    registration_ids = [item.id for item in registrations]
    public_ids = [item.registration_id for item in registrations]
    verified = len([item for item in registrations if item.status == "verified" or item.verified_at is not None])
    ideas = db.execute(select(func.count()).select_from(Idea).where(Idea.user_id == user.id)).scalar_one()
    team_ids = _team_ids(db, user)
    teams = len(team_ids)
    pending_transfers = db.execute(
        select(func.count()).select_from(OwnershipTransfer).where(
            or_(OwnershipTransfer.from_user_id == user.id, OwnershipTransfer.to_user_id == user.id),
            OwnershipTransfer.status.in_(["pending_recipient", "recipient_accepted"]),
        )
    ).scalar_one()
    active_disputes = db.execute(
        select(func.count()).select_from(Dispute).where(
            or_(Dispute.claimant_id == user.id, Dispute.respondent_id == user.id),
            Dispute.status.in_(["open", "under_review", "evidence_requested"]),
        )
    ).scalar_one()
    new_alerts = db.execute(
        select(func.count()).select_from(TheftAlert).where(
            TheftAlert.owner_id == user.id,
            TheftAlert.status.in_(["new", "under_review"]),
        )
    ).scalar_one()
    unread = db.execute(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    ).scalar_one()
    proofs = db.execute(
        select(func.count()).select_from(ZkpProof).where(ZkpProof.user_id == user.id, ZkpProof.status == "verified")
    ).scalar_one()
    active_shares = db.execute(
        select(func.count()).select_from(VerificationRequest).where(
            VerificationRequest.creator_id == user.id,
            VerificationRequest.status.in_(["pending", "verified"]),
        )
    ).scalar_one()

    now = utcnow()
    monthly = []
    parsed_months = []
    for offset in range(5, -1, -1):
        year = now.year
        month = now.month - offset
        while month <= 0:
            month += 12
            year -= 1
        parsed_months.append((year, month))
    for year, month in parsed_months:
        count = len([item for item in registrations if item.registered_at.year == year and item.registered_at.month == month])
        monthly.append({"label": f"{year}-{month:02d}", "registrations": count})
    asset_types = Counter(item.asset_type for item in registrations)
    ledger_status = ledger_service.status()

    heatmap_days = {}
    heatmap_start = (now - timedelta(days=181)).date()

    def bump(value, key):
        if value is None:
            return
        day = value.date()
        if day < heatmap_start:
            return
        entry = heatmap_days.setdefault(day.isoformat(), {"registrations": 0, "ideas": 0, "proofs": 0, "versions": 0})
        entry[key] += 1

    for item in registrations:
        bump(item.registered_at, "registrations")
    for created_at in db.execute(select(Idea.created_at).where(Idea.user_id == user.id)).scalars().all():
        bump(created_at, "ideas")
    for created_at in db.execute(select(ZkpProof.created_at).where(ZkpProof.user_id == user.id)).scalars().all():
        bump(created_at, "proofs")
    if registration_ids:
        for created_at in db.execute(
            select(CreativeVersion.created_at).where(CreativeVersion.registration_id.in_(registration_ids))
        ).scalars().all():
            bump(created_at, "versions")
    activity_heatmap = []
    for offset in range(182):
        day = heatmap_start + timedelta(days=offset)
        entry = heatmap_days.get(day.isoformat(), {"registrations": 0, "ideas": 0, "proofs": 0, "versions": 0})
        entry["date"] = day.isoformat()
        entry["total"] = entry["registrations"] + entry["ideas"] + entry["proofs"] + entry["versions"]
        activity_heatmap.append(entry)

    return {
        "stats": {
            "total_creations": len(registrations),
            "owned_creations": len([item for item in registrations if item.user_id == user.id]),
            "incoming_ownership": len([item for item in registrations if item.id in pending_ids]),
            "verified_records": verified,
            "protected_ideas": ideas,
            "team_projects": teams,
            "pending_transfers": pending_transfers,
            "active_disputes": active_disputes,
            "security_alerts": new_alerts,
            "unread_notifications": unread,
            "verified_proofs": proofs,
            "active_shares": active_shares,
        },
        "charts": {
            "registrations_by_month": monthly,
            "asset_types": [{"name": key, "value": value} for key, value in asset_types.most_common()],
            "verification_split": [
                {"name": "Verified", "value": verified},
                {"name": "Pending verification", "value": max(0, len(registrations) - verified)},
            ],
            "activity_heatmap": activity_heatmap,
        },
        "ledger": {
            "mode": ledger_status.get("mode", "simulation"),
            "network": ledger_status.get("network", "AUTHENTIQ Local Ledger"),
        },
        "scope": {
            "user_id": user.id,
            "organization_id": user.organization_id,
            "registration_ids_sample": public_ids[:5],
            "registration_ids_count": len(registration_ids),
        },
    }


@router.get("/activity")
def activity(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registrations, pending_ids = _scoped_registrations(db, user)
    registrations = sorted(registrations, key=lambda item: item.registered_at, reverse=True)[:6]
    names = {registration.user_id: (db.get(User, registration.user_id).display_name if db.get(User, registration.user_id) else None) for registration in registrations}
    entities = _entity_ids(db, user)
    transactions = db.execute(
        select(LedgerTransaction)
        .where(or_(LedgerTransaction.actor_id == user.id, LedgerTransaction.entity_id.in_(entities)))
        .order_by(LedgerTransaction.timestamp.desc())
        .limit(8)
    ).scalars().all() if entities else db.execute(
        select(LedgerTransaction).where(LedgerTransaction.actor_id == user.id).order_by(LedgerTransaction.timestamp.desc()).limit(8)
    ).scalars().all()
    audits = db.execute(
        select(AuditLog)
        .where(or_(AuditLog.actor_id == user.id, AuditLog.entity_id.in_(entities)))
        .order_by(AuditLog.created_at.desc())
        .limit(12)
    ).scalars().all() if entities else db.execute(
        select(AuditLog).where(AuditLog.actor_id == user.id).order_by(AuditLog.created_at.desc()).limit(12)
    ).scalars().all()
    alerts = db.execute(
        select(TheftAlert).where(TheftAlert.owner_id == user.id).order_by(TheftAlert.created_at.desc()).limit(5)
    ).scalars().all()
    alerts_reg = {item.id: item for item in db.execute(select(Registration).where(Registration.id.in_({a.registration_id for a in alerts} | {a.matched_registration_id for a in alerts}))).scalars().all()} if alerts else {}
    shares = db.execute(
        select(VerificationRequest).where(VerificationRequest.creator_id == user.id).order_by(VerificationRequest.created_at.desc()).limit(5)
    ).scalars().all()
    share_regs = {item.id: item for item in db.execute(select(Registration).where(Registration.id.in_([s.registration_id for s in shares]))).scalars().all()} if shares else {}
    team_notifications = db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.type.in_(["team", "team_invitation", "ownership", "contribution"])).order_by(Notification.created_at.desc()).limit(5)
    ).scalars().all()
    return {
        "recent_registrations": [
            {
                **registration_out(item, names.get(item.user_id)),
                "ownership_status": "owned" if item.user_id == user.id else "pending_confirmation",
                "pending_ownership": item.user_id != user.id,
            }
            for item in registrations
        ],
        "ledger_transactions": [ledger_out(item) for item in transactions],
        "audit_timeline": [audit_out(item) for item in audits],
        "verification_activity": [
            {
                "id": item.id,
                "verification_id": item.verification_id,
                "registration": share_regs.get(item.registration_id).registration_id if share_regs.get(item.registration_id) else None,
                "status": item.status,
                "result": item.result,
                "uses": item.uses,
                "max_uses": item.max_uses,
                "created_at": item.created_at.isoformat(),
                "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            }
            for item in shares
        ],
        "alerts": [alert_out(item, alerts_reg.get(item.registration_id), alerts_reg.get(item.matched_registration_id)) for item in alerts],
        "team_activity": [notification_out(item) for item in team_notifications],
        "quick_actions": [
            {"label": "Register New Creation", "path": "/register", "icon": "PlusCircle"},
            {"label": "Protect a New Idea", "path": "/ideas", "icon": "Lightbulb"},
            {"label": "Verify Ownership", "path": "/anonymous-verification", "icon": "ShieldCheck"},
            {"label": "Invite Team Member", "path": "/teams", "icon": "Users"},
        ],
    }
