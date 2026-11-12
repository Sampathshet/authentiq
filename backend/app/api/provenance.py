from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ledger import ledger_service
from app.models import AIProvenance, FileMetadata, Registration, User
from app.schemas.content import ProvenanceAnalyzeRequest, ProvenanceRecordRequest
from app.security.crypto import sha256_text, utcnow
from app.services.access import registration_or_404, require_registration_access, require_registration_owner
from app.services.analysis import build_ai_analysis
from app.services.audit import append_audit
from app.services.notifications import notify
from app.services.serializers import provenance_out

router = APIRouter(prefix="/provenance", tags=["AI provenance"])


@router.post("/analyze")
def analyze(
    payload: ProvenanceAnalyzeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    require_registration_access(user, registration, db)
    metadata = db.execute(select(FileMetadata).where(FileMetadata.registration_id == registration.id)).scalar_one_or_none()
    analysis = build_ai_analysis(registration, metadata)
    append_audit(
        db,
        "ai_analysis_run",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"analysis_available": analysis.get("analysis_available"), "method": analysis.get("method")},
    )
    db.commit()
    return {
        "registration_id": registration.registration_id,
        "analysis": analysis,
        "disclaimer": "AI-content detection is probabilistic. AUTHENTIQ reports only signals that were actually inspected and never fabricates classifier output.",
    }


@router.post("/record", status_code=status.HTTP_201_CREATED)
def record_provenance(
    payload: ProvenanceRecordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    require_registration_owner(user, registration, db)
    if payload.declared_ai and not (payload.model_name or payload.tool_name):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide at least a model or tool name when declaring AI involvement")
    metadata = db.execute(select(FileMetadata).where(FileMetadata.registration_id == registration.id)).scalar_one_or_none()
    analysis = build_ai_analysis(registration, metadata)
    prompt_commitment = None
    if payload.prompt_commitment:
        raw = payload.prompt_commitment.strip()
        prompt_commitment = raw if raw.startswith("0x") else f"sha256:{sha256_text(raw)}"
    record = AIProvenance(
        registration_id=registration.id,
        user_id=user.id,
        declared_ai=payload.declared_ai,
        model_name=payload.model_name,
        tool_name=payload.tool_name,
        prompt_commitment=prompt_commitment,
        human_contribution=payload.human_contribution,
        editing_details=payload.editing_details,
        creation_date=payload.creation_date,
        analysis_available=bool(analysis.get("analysis_available")),
        analysis=analysis,
    )
    db.add(record)
    db.flush()
    tx = ledger_service.record_provenance(db, user.id, registration, record)
    record.ledger_tx_id = tx.tx_id
    append_audit(
        db,
        "provenance_recorded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"declared_ai": record.declared_ai, "model": record.model_name, "ledger_tx_id": record.ledger_tx_id},
    )
    notify(
        db,
        user.id,
        "provenance",
        "Provenance record attached",
        f"AI provenance information was attached to {registration.registration_id}.",
        "registration",
        registration.id,
    )
    db.commit()
    return provenance_out(record)


@router.get("")
def list_provenance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registrations = db.execute(select(Registration).where(Registration.user_id == user.id)).scalars().all()
    registration_ids = [registration.id for registration in registrations]
    records = db.execute(
        select(AIProvenance)
        .where(AIProvenance.registration_id.in_(registration_ids))
        .order_by(AIProvenance.created_at.desc())
        .limit(100)
    ).scalars().all() if registration_ids else []
    labels = {registration.id: registration.registration_id for registration in registrations}
    return {
        "items": [
            {**provenance_out(record), "registration_label": labels.get(record.registration_id)}
            for record in records
        ]
    }


@router.get("/{registration_id}")
def get_provenance(registration_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, registration_id)
    require_registration_access(user, registration, db)
    records = db.execute(
        select(AIProvenance)
        .where(AIProvenance.registration_id == registration.id)
        .order_by(AIProvenance.created_at.desc())
    ).scalars().all()
    metadata = db.execute(select(FileMetadata).where(FileMetadata.registration_id == registration.id)).scalar_one_or_none()
    return {
        "registration": {
            "id": registration.id,
            "registration_id": registration.registration_id,
            "title": registration.title,
            "file_name": registration.file_name,
            "asset_type": registration.asset_type,
            "metadata": {
                "mime_type": metadata.mime_type if metadata else registration.mime_type,
                "extension": metadata.extension if metadata else None,
                "size_bytes": metadata.size_bytes if metadata else registration.file_size,
            } if metadata else None,
        },
        "items": [provenance_out(record) for record in records],
        "analysis_available": bool(records) and records[0].analysis_available,
        "disclaimer": "Declarations are self-reported and recorded with the creator's identity. Optional analysis is probabilistic and limited to inspected metadata.",
    }
