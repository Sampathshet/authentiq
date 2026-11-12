from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AuditLog, Registration, TheftAlert, User
from app.services.audit import verify_audit_chain
from app.services.integrity import workspace_overview

router = APIRouter(prefix="/integrity", tags=["integrity"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payload = workspace_overview(db, user)
    audit = verify_audit_chain(db)
    payload["audit_chain"] = {
        "valid": audit["valid"],
        "events": audit["events"],
        "errors": audit["errors"],
        "last_hash": audit["last_hash"],
    }
    payload["exposure"] = {
        "open_alerts": db.execute(
            select(func.count())
            .select_from(TheftAlert)
            .where(TheftAlert.owner_id == user.id, TheftAlert.status == "open")
        ).scalar_one(),
        "public_fingerprint_records": db.execute(
            select(func.count())
            .select_from(Registration)
            .where(Registration.user_id == user.id, Registration.privacy != "private")
        ).scalar_one(),
        "audit_events": db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == user.id)
        ).scalar_one(),
    }
    return payload
