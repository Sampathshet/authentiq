import hashlib
import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.fingerprint.sha256 import sha256_bytes
from app.ledger import ledger_service
from app.models import Idea, IdeaRevision, User
from app.schemas.content import (
    IdeaCreateRequest,
    IdeaNotesUpdateRequest,
    IdeaRevisionCreateRequest,
)
from app.security.crypto import decrypt_text, encrypt_text, utcnow
from app.services.audit import append_audit
from app.services.certificate import build_idea_certificate, verification_url_for
from app.services.notifications import notify
from app.services.serializers import idea_out
from app.zkp.sigma import create_commitment

router = APIRouter(prefix="/ideas", tags=["idea protection vault"])


def _idea_or_404(db: Session, identifier: str) -> Idea:
    idea = db.get(Idea, identifier)
    if not idea:
        idea = db.execute(select(Idea).where(Idea.idea_ref == identifier)).scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Protected idea not found")
    return idea


def _require_owner(user: User, idea: Idea):
    if idea.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this protected idea")


def _new_ref() -> str:
    return f"IDEA-{datetime.now(timezone.utc).year}-{secrets.token_hex(4).upper()}"


@router.post("", status_code=status.HTTP_201_CREATED)
def create_idea(
    payload: IdeaCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content_hash = sha256_bytes((payload.title + "\n" + payload.description).encode("utf-8"))
    commitment = create_commitment(content_hash)
    ref = _new_ref()
    idea = Idea(
        idea_ref=ref,
        user_id=user.id,
        organization_id=user.organization_id,
        title=payload.title,
        description_encrypted=encrypt_text(payload.description),
        commitment=commitment["poseidon_commitment"],
        secret_encrypted=encrypt_text(format(commitment["secret_int"], "064x")),
        privacy=payload.privacy,
        status="protected",
        is_demo=user.is_demo,
    )
    db.add(idea)
    db.flush()
    tx = ledger_service.register_idea(db, user.id, idea)
    idea.ledger_tx_id = tx.tx_id
    append_audit(
        db,
        "idea_commitment_created",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="idea",
        entity_id=idea.idea_ref,
        metadata={"commitment": idea.commitment, "privacy": idea.privacy, "ledger_tx_id": idea.ledger_tx_id},
    )
    notify(
        db,
        user.id,
        "idea",
        "Idea protected",
        f"{idea.title} was protected with commitment {idea.commitment[:18]}...",
        "idea",
        idea.id,
    )
    db.commit()
    return idea_out(idea, payload.description, include_private=True)


@router.get("")
def list_ideas(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    ideas = db.execute(
        select(Idea).where(Idea.user_id == user.id).order_by(Idea.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "items": [idea_out(idea, None, include_private=True) for idea in ideas],
        "total": len(ideas),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{identifier}")
def get_idea(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    idea = _idea_or_404(db, identifier)
    _require_owner(user, idea)
    revisions = db.execute(
        select(IdeaRevision).where(IdeaRevision.idea_id == idea.id).order_by(IdeaRevision.revision_no.asc())
    ).scalars().all()
    payload = idea_out(idea, decrypt_text(idea.description_encrypted), include_private=True)
    payload["revisions"] = [
        {
            "id": revision.id,
            "revision_no": revision.revision_no,
            "notes": decrypt_text(revision.notes_encrypted),
            "commitment": revision.commitment,
            "ledger_tx_id": revision.ledger_tx_id,
            "created_at": revision.created_at.isoformat(),
        }
        for revision in revisions
    ]
    payload["ledger_tx_id"] = idea.ledger_tx_id
    return payload


@router.post("/{identifier}/revisions", status_code=status.HTTP_201_CREATED)
def add_revision(
    identifier: str,
    payload: IdeaRevisionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    idea = _idea_or_404(db, identifier)
    _require_owner(user, idea)
    latest = db.execute(
        select(IdeaRevision).where(IdeaRevision.idea_id == idea.id).order_by(IdeaRevision.revision_no.desc()).limit(1)
    ).scalar_one_or_none()
    commit = create_commitment(sha256_bytes(payload.notes.encode("utf-8")))
    revision = IdeaRevision(
        idea_id=idea.id,
        revision_no=(latest.revision_no + 1) if latest else 1,
        notes_encrypted=encrypt_text(payload.notes),
        commitment=commit["poseidon_commitment"],
    )
    db.add(revision)
    db.flush()
    tx = ledger_service.record_idea_revision(db, user.id, idea, revision)
    revision.ledger_tx_id = tx.tx_id
    append_audit(
        db,
        "idea_revision_recorded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="idea",
        entity_id=idea.idea_ref,
        metadata={"revision_no": revision.revision_no, "commitment": revision.commitment},
    )
    db.commit()
    return {
        "id": revision.id,
        "revision_no": revision.revision_no,
        "commitment": revision.commitment,
        "ledger_tx_id": revision.ledger_tx_id,
        "created_at": revision.created_at.isoformat(),
        "original_commitment_preserved": idea.commitment,
    }


@router.patch("/{identifier}/notes")
def update_notes(
    identifier: str,
    payload: IdeaNotesUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    idea = _idea_or_404(db, identifier)
    _require_owner(user, idea)
    latest = db.execute(
        select(IdeaRevision).where(IdeaRevision.idea_id == idea.id).order_by(IdeaRevision.revision_no.desc()).limit(1)
    ).scalar_one_or_none()
    revision = IdeaRevision(
        idea_id=idea.id,
        revision_no=(latest.revision_no + 1) if latest else 1,
        notes_encrypted=encrypt_text(payload.notes),
        commitment=create_commitment(sha256_bytes(payload.notes.encode("utf-8")))["poseidon_commitment"],
    )
    db.add(revision)
    db.flush()
    append_audit(
        db,
        "idea_notes_updated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="idea",
        entity_id=idea.idea_ref,
        metadata={"revision_no": revision.revision_no},
    )
    db.commit()
    return {"message": "Private notes updated without changing the original idea commitment", "revision_no": revision.revision_no}


@router.post("/{identifier}/reveal")
def reveal_idea(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    idea = _idea_or_404(db, identifier)
    _require_owner(user, idea)
    if idea.status != "revealed":
        idea.status = "revealed"
        idea.revealed_at = utcnow()
        append_audit(
            db,
            "idea_revealed",
            actor_id=user.id,
            actor_ref=user.email,
            entity_type="idea",
            entity_id=idea.idea_ref,
        )
        db.commit()
    return {
        "idea_ref": idea.idea_ref,
        "title": idea.title,
        "description": decrypt_text(idea.description_encrypted),
        "commitment": idea.commitment,
        "revealed_at": idea.revealed_at.isoformat(),
        "warning": "Revealing the description does not alter the private commitment or the ledger record.",
    }


@router.get("/{identifier}/certificate")
def idea_certificate(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    idea = _idea_or_404(db, identifier)
    _require_owner(user, idea)
    pdf = build_idea_certificate(idea, user.display_name, verification_url_for(idea.idea_ref))
    append_audit(
        db,
        "idea_certificate_downloaded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="idea",
        entity_id=idea.idea_ref,
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AUTHENTIQ-{idea.idea_ref}.pdf"'},
    )


@router.get("/{identifier}/evidence")
def idea_evidence(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    idea = _idea_or_404(db, identifier)
    _require_owner(user, idea)
    revisions = db.execute(
        select(IdeaRevision).where(IdeaRevision.idea_id == idea.id).order_by(IdeaRevision.revision_no.asc())
    ).scalars().all()
    ledger_record = ledger_service.verify_record(idea.ledger_tx_id) if idea.ledger_tx_id else None
    evidence = {
        "format": "AUTHENTIQ-IDEA-EVIDENCE-V1",
        "idea_ref": idea.idea_ref,
        "title": idea.title,
        "commitment": idea.commitment,
        "secret_revealed": False,
        "privacy": idea.privacy,
        "status": idea.status,
        "created_at": idea.created_at.isoformat(),
        "ledger_mode": idea.ledger_mode,
        "ledger_tx_id": idea.ledger_tx_id,
        "ledger_record": ledger_record,
        "revisions": [
            {
                "revision_no": revision.revision_no,
                "commitment": revision.commitment,
                "ledger_tx_id": revision.ledger_tx_id,
                "created_at": revision.created_at.isoformat(),
            }
            for revision in revisions
        ],
        "note": "The original idea content remains encrypted and is not included in this evidence package unless the owner explicitly reveals it.",
    }
    append_audit(
        db,
        "idea_evidence_downloaded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="idea",
        entity_id=idea.idea_ref,
    )
    db.commit()
    return Response(
        content=json.dumps(evidence, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="AUTHENTIQ-{idea.idea_ref}-evidence.json"'},
    )
