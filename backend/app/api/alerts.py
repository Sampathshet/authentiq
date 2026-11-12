from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import FileMetadata, Registration, SimilarityAnalysis, TheftAlert, User
from app.schemas.content import AlertStatusRequest
from app.security.crypto import utcnow
from app.services.audit import append_audit
from app.services.serializers import alert_out

router = APIRouter(prefix="/alerts", tags=["ownership theft alerts"])


def _alert_or_404(db: Session, alert_id: str, user: User) -> TheftAlert:
    alert = db.get(TheftAlert, alert_id)
    if not alert or alert.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.get("")
def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    alert_type: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(TheftAlert).where(TheftAlert.owner_id == user.id)
    if status_filter:
        query = query.where(TheftAlert.status == status_filter)
    if alert_type:
        query = query.where(TheftAlert.alert_type == alert_type)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    alerts = db.execute(
        query.order_by(TheftAlert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    registration_ids = {alert.registration_id for alert in alerts} | {alert.matched_registration_id for alert in alerts}
    registrations = {
        registration.id: registration
        for registration in db.execute(select(Registration).where(Registration.id.in_(registration_ids))).scalars().all()
    } if registration_ids else {}
    counts = {
        row[0]: row[1]
        for row in db.execute(
            select(TheftAlert.status, func.count()).where(TheftAlert.owner_id == user.id).group_by(TheftAlert.status)
        ).all()
    }
    return {
        "items": [
            alert_out(alert, registrations.get(alert.registration_id), registrations.get(alert.matched_registration_id))
            for alert in alerts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "counts": counts,
    }


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    alert = _alert_or_404(db, alert_id, user)
    registration = db.get(Registration, alert.registration_id)
    matched = db.get(Registration, alert.matched_registration_id)
    metadata = db.execute(
        select(FileMetadata).where(FileMetadata.registration_id.in_([alert.registration_id, alert.matched_registration_id]))
    ).scalars().all()
    similarities = db.execute(
        select(SimilarityAnalysis).where(
            SimilarityAnalysis.registration_id == alert.registration_id,
            SimilarityAnalysis.compared_registration_id == alert.matched_registration_id,
        )
    ).scalars().all()
    payload = alert_out(alert, registration, matched)
    payload["matched_registration"] = {
        "registration_id": matched.registration_id if matched else None,
        "title": matched.title if matched else None,
        "fingerprint": matched.sha256 if matched else None,
        "registered_at": matched.registered_at.isoformat() if matched else None,
        "status": matched.status if matched else None,
        "ledger_tx_id": matched.ledger_tx_id if matched else None,
        "is_owner": bool(matched and matched.user_id == user.id),
    }
    payload["metadata"] = [
        {
            "registration_id": item.registration_id,
            "original_name": item.original_name,
            "mime_type": item.mime_type,
            "size_bytes": item.size_bytes,
            "perceptual_hash": item.perceptual_hash,
        }
        for item in metadata
    ]
    payload["similarity_analyses"] = [
        {"method": item.method, "score": item.score, "details": item.details, "created_at": item.created_at.isoformat()}
        for item in similarities
    ]
    payload["disclaimer"] = "Similarity indicators are investigation aids, not findings of infringement. Exact SHA-256 matches indicate byte-identical files."
    return payload


@router.patch("/{alert_id}/status")
def update_alert(
    alert_id: str,
    payload: AlertStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = _alert_or_404(db, alert_id, user)
    alert.status = payload.status
    if payload.investigation_notes is not None:
        alert.investigation_notes = payload.investigation_notes
    if payload.status in {"resolved", "dismissed"}:
        alert.reviewed_at = utcnow()
    append_audit(
        db,
        "theft_alert_updated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="theft_alert",
        entity_id=alert.id,
        metadata={"status": alert.status, "alert_type": alert.alert_type},
    )
    db.commit()
    return alert_out(alert)
