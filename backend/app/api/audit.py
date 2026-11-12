from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AuditLog, User
from app.services.audit import verify_audit_chain
from app.services.serializers import audit_out

router = APIRouter(prefix="/audit-logs", tags=["audit logs"])


@router.get("")
def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    action: str | None = None,
    entity_type: str | None = None,
    scope: str = Query(default="mine", pattern="^(mine|all)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(AuditLog)
    if scope == "all" and user.role not in {"verifier", "org_admin"}:
        query = query.where(AuditLog.actor_id == user.id)
    elif scope == "mine":
        query = query.where(or_(AuditLog.actor_id == user.id, AuditLog.actor_ref == user.email))
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    items = db.execute(
        query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "items": [audit_out(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "append_only": True,
    }


@router.get("/verify")
def verify_chain(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return verify_audit_chain(db)
