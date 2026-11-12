from sqlalchemy.orm import Session

from app.models import Notification


def notify(
    db: Session,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> Notification:
    item = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(item)
    db.flush()
    return item


def notify_many(
    db: Session,
    user_ids: list[str],
    notification_type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> list[Notification]:
    items = []
    for user_id in dict.fromkeys(user_ids):
        items.append(notify(db, user_id, notification_type, title, message, entity_type, entity_id))
    return items
