from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ledger import ledger_service
from app.models import (
    Dispute,
    Idea,
    LedgerTransaction,
    OwnershipTransfer,
    Registration,
    TeamMember,
    TeamProject,
    User,
    VerificationRequest,
)
from app.services.audit import append_audit
from app.services.serializers import ledger_out

router = APIRouter(prefix="/ledger", tags=["ledger"])


def _entities(db: Session, user: User) -> list[str]:
    registrations = db.execute(select(Registration).where(Registration.user_id == user.id)).scalars().all()
    ideas = db.execute(select(Idea).where(Idea.user_id == user.id)).scalars().all()
    team_ids = set(db.execute(select(TeamMember.project_id).where(TeamMember.user_id == user.id)).scalars().all())
    team_ids |= set(db.execute(select(TeamProject.id).where(TeamProject.owner_id == user.id)).scalars().all())
    transfers = db.execute(select(OwnershipTransfer.id).where(or_(OwnershipTransfer.from_user_id == user.id, OwnershipTransfer.to_user_id == user.id))).scalars().all()
    disputes = db.execute(select(Dispute.dispute_ref).where(or_(Dispute.claimant_id == user.id, Dispute.respondent_id == user.id))).scalars().all()
    shares = db.execute(select(VerificationRequest.verification_id).where(VerificationRequest.creator_id == user.id)).scalars().all()
    return [item.registration_id for item in registrations] + [item.idea_ref for item in ideas] + list(team_ids) + list(transfers) + list(disputes) + list(shares)


@router.get("/status")
def ledger_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    state = ledger_service.status()
    latest = db.execute(select(LedgerTransaction).order_by(LedgerTransaction.timestamp.desc()).limit(1)).scalar_one_or_none()
    state["latest_transaction"] = ledger_out(latest) if latest else None
    state["database_records"] = db.execute(select(func.count()).select_from(LedgerTransaction)).scalar_one()
    return state


@router.get("/transactions")
def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tx_type: str | None = None,
    scope: str = Query(default="mine", pattern="^(mine|all)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(LedgerTransaction)
    if scope == "all":
        if user.role not in {"verifier", "org_admin"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only verifier or organization admin roles can list all ledger events")
    else:
        entities = _entities(db, user)
        query = query.where(or_(LedgerTransaction.actor_id == user.id, LedgerTransaction.entity_id.in_(entities)))
    if tx_type:
        query = query.where(LedgerTransaction.tx_type == tx_type)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    transactions = db.execute(
        query.order_by(LedgerTransaction.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "items": [ledger_out(item) for item in transactions],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "ledger_mode": ledger_service.adapter.mode,
        "simulated": ledger_service.adapter.mode == "simulation",
    }


@router.get("/transactions/{tx_id}")
def get_transaction(tx_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    transaction = db.execute(select(LedgerTransaction).where(LedgerTransaction.tx_id == tx_id)).scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger transaction not found")
    owned = transaction.actor_id == user.id or transaction.entity_id in _entities(db, user)
    if not owned and user.role not in {"verifier", "org_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this ledger event")
    raw = ledger_service.get_transaction(tx_id)
    payload = ledger_out(transaction)
    payload["raw_ledger_record"] = raw
    payload["integrity"] = {
        "database_digest": transaction.payload_digest,
        "ledger_payload_digest": (raw or {}).get("payload_digest"),
        "matches": bool(raw and raw.get("payload_digest") == transaction.payload_digest),
    }
    return payload


@router.post("/audit")
def audit(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = ledger_service.audit()
    append_audit(
        db,
        "ledger_audit_run",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="ledger",
        entity_id=ledger_service.adapter.mode,
        metadata={"valid": report.get("valid"), "records": report.get("records"), "errors": report.get("errors")},
    )
    db.commit()
    return report
