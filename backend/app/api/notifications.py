from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Notification, User
from app.security.crypto import utcnow
from app.services.serializers import notification_out

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    unread_only: bool = False,
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    if category:
        query = query.where(Notification.type == category)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    unread = db.execute(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    ).scalar_one()
    items = db.execute(
        query.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "items": [notification_out(item) for item in items],
        "total": total,
        "unread": unread,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.patch("/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    item.is_read = True
    db.commit()
    return notification_out(item)


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    ).scalars().all()
    for item in items:
        item.is_read = True
    db.commit()
    return {"message": f"{len(items)} notifications marked as read", "updated": len(items)}


@router.delete("/{notification_id}")
def delete_notification(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Notification, notification_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    db.delete(item)
    db.commit()
    return {"message": "Notification dismissed"}
