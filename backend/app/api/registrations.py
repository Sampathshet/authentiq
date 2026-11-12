from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.fingerprint.chunking import merkle_root
from app.fingerprint.sha256 import sha256_bytes
from app.ledger import ledger_service
from app.models import (
    CreativeVersion,
    FileMetadata,
    Registration,
    TeamMember,
    TeamProject,
    Upload,
    User,
    ZkpProof,
)
from app.schemas.content import DuplicateCheckRequest, FingerprintVerifyRequest, RegistrationCreateRequest
from app.security.crypto import sha256_hex
from app.services.access import (
    registration_or_404,
    require_registration_access,
    require_registration_owner,
)
from app.services.audit import append_audit
from app.services.certificate import build_registration_certificate, verification_url_for
from app.services.integrity import build_evidence_packet, trust_report
from app.services.ownership import ownership_chain, ownership_state, pending_registration_ids
from app.services.registration_service import create_registration, duplicate_report
from app.services.serializers import registration_out
from app.services.team_context import active_membership, team_context
from app.storage.files import iter_decrypted
from app.zkp.verification_key import verification_key_for

router = APIRouter(prefix="/registrations", tags=["registrations"])


def _owner_names(db: Session, registrations) -> dict[str, str]:
    ids = {registration.user_id for registration in registrations}
    if not ids:
        return {}
    users = db.execute(select(User).where(User.id.in_(ids))).scalars().all()
    return {user.id: user.display_name for user in users}


def _team_names(db: Session, registrations) -> dict[str, str]:
    ids = {registration.team_project_id for registration in registrations if registration.team_project_id}
    if not ids:
        return {}
    projects = db.execute(select(TeamProject).where(TeamProject.id.in_(ids))).scalars().all()
    return {project.id: project.name for project in projects}


def _user_team_ids(db: Session, user: User) -> list[str]:
    """Team projects the user owns or is an active member of."""
    member_projects = db.execute(
        select(TeamMember.project_id).where(
            TeamMember.user_id == user.id,
            TeamMember.status == "active",
        )
    ).scalars().all()
    owned_projects = db.execute(
        select(TeamProject.id).where(TeamProject.owner_id == user.id)
    ).scalars().all()
    return list({*member_projects, *owned_projects})


@router.post("", status_code=status.HTTP_201_CREATED)
def register_creation(
    payload: RegistrationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    upload = db.get(Upload, payload.upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    if upload.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload must be completed before registration")
    if not upload.final_sha256:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload does not have a verified fingerprint")
    try:
        registration, metadata, alerts = create_registration(
            db,
            user,
            upload,
            payload.title,
            payload.description,
            payload.asset_type,
            payload.privacy,
            payload.creation_timestamp,
            payload.tags,
            payload.team_id,
            payload.scope_to_organization,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    duplicates = duplicate_report(
        db,
        user,
        registration.sha256,
        metadata.perceptual_hash,
        exclude_registration_id=registration.id,
    )
    team = team_context(db, registration)
    return {
        "registration": registration_out(
            registration,
            user.display_name,
            metadata,
            team_name=team["name"] if team else None,
        ),
        "team": team,
        "alerts_created": len(alerts),
        "duplicates": duplicates,
        "ledger": {
            "mode": registration.ledger_mode,
            "tx_id": registration.ledger_tx_id,
            "simulated": registration.ledger_mode == "simulation",
        },
        "certificate_url": f"{settings.api_prefix}/registrations/{registration.id}/certificate",
        "verification_key": verification_key_for(registration),
    }


@router.post("/duplicate-check")
def check_duplicates(
    payload: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return duplicate_report(db, user, payload.sha256.lower(), payload.perceptual_hash)


@router.get("")
def list_registrations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=200),
    asset_type: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    sort: str = Query(default="recent", pattern="^(recent|oldest|title)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = [Registration.user_id == user.id]
    if user.organization_id:
        filters = [or_(Registration.user_id == user.id, Registration.organization_id == user.organization_id)]
    pending_ids = pending_registration_ids(db, user)
    if pending_ids:
        filters = [or_(*filters, Registration.id.in_(pending_ids))]
    team_ids = _user_team_ids(db, user)
    if team_ids:
        filters = [or_(*filters, Registration.team_project_id.in_(team_ids))]
    query = select(Registration).where(*filters)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                Registration.title.ilike(pattern),
                Registration.registration_id.ilike(pattern),
                Registration.sha256.ilike(pattern),
                Registration.file_name.ilike(pattern),
            )
        )
    if asset_type:
        query = query.where(Registration.asset_type == asset_type)
    if status_filter:
        query = query.where(Registration.status == status_filter)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    order = {
        "recent": Registration.registered_at.desc(),
        "oldest": Registration.registered_at.asc(),
        "title": Registration.title.asc(),
    }[sort]
    items = db.execute(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    names = _owner_names(db, items)
    team_names = _team_names(db, items)
    metadata_map = {
        item.registration_id: item
        for item in db.execute(
            select(FileMetadata).where(FileMetadata.registration_id.in_([r.id for r in items]))
        ).scalars().all()
    } if items else {}
    payloads = []
    for item in items:
        payload = registration_out(
            item,
            names.get(item.user_id),
            metadata_map.get(item.id),
            team_name=team_names.get(item.team_project_id) if item.team_project_id else None,
        )
        payload["ownership_status"] = (
            "owned" if item.user_id == user.id or item.id not in pending_ids else "pending_confirmation"
        )
        payload["pending_ownership"] = item.id in pending_ids and item.user_id != user.id
        payloads.append(payload)
    return {
        "items": payloads,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{identifier}")
def get_registration(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, identifier)
    require_registration_access(user, registration, db)
    metadata = db.execute(
        select(FileMetadata).where(FileMetadata.registration_id == registration.id)
    ).scalar_one_or_none()
    owner = db.get(User, registration.user_id)
    version_count = db.execute(
        select(func.count()).select_from(CreativeVersion).where(CreativeVersion.registration_id == registration.id)
    ).scalar_one()
    proof_count = db.execute(
        select(func.count()).select_from(ZkpProof).where(ZkpProof.registration_id == registration.id)
    ).scalar_one()
    payload = registration_out(registration, owner.display_name if owner else None, metadata)
    payload["version_count"] = version_count
    payload["proof_count"] = proof_count
    payload["has_private_access"] = True
    team = team_context(db, registration)
    if team:
        payload["team"] = team
        payload["team_name"] = team["name"]
        payload["team_id"] = team["id"]
    payload["team_membership"] = (
        {
            "role": membership.role,
            "status": membership.status,
            "percent": next(
                (
                    member["percent"]
                    for member in team["members"]
                    if member["id"] == membership.id
                ),
                0.0,
            ),
        }
        if team and (membership := active_membership(db, team["id"], user))
        else None
    )
    ownership = ownership_state(db, registration, user)
    payload["ownership"] = ownership
    payload["ownership_status"] = ownership["status"]
    payload["file"] = {
        "original_name": metadata.original_name if metadata else registration.file_name,
        "mime_type": metadata.mime_type if metadata else registration.mime_type,
        "extension": metadata.extension if metadata else "",
        "size_bytes": metadata.size_bytes if metadata else registration.file_size,
        "encrypted_size_bytes": metadata.encrypted_size_bytes if metadata else 0,
        "chunk_count": metadata.chunk_count if metadata else 1,
        "perceptual_hash": metadata.perceptual_hash if metadata else None,
        "extracted_text": (metadata.extracted_text[:4000] if metadata and metadata.extracted_text else None),
        "stored": bool(registration.storage_path) and Path(registration.storage_path).exists(),
    }
    return payload


@router.get("/{identifier}/ownership-chain")
def get_ownership_chain(
    identifier: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, identifier)
    require_registration_access(user, registration, db)
    payload = ownership_chain(db, registration)
    payload["ownership"] = ownership_state(db, registration, user)
    return payload


@router.get("/{identifier}/verification-key")
def get_verification_key(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, identifier)
    require_registration_owner(user, registration, db)
    return {
        "registration_id": registration.registration_id,
        "verification_key": verification_key_for(registration),
        "format": "aqv1_<opening>_<blinding>",
        "warning": "Treat this key like a private credential. Anyone who holds it can prove ownership of this registration. It cannot decrypt the original file.",
    }


@router.get("/{identifier}/file")
def download_registration_file(
    identifier: str,
    inline: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, identifier)
    require_registration_access(user, registration, db)
    path = Path(registration.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Stored file is no longer available")
    disposition = "inline" if inline else "attachment"
    safe_name = registration.file_name.replace('"', "")
    headers = {
        "Content-Disposition": f'{disposition}; filename="{safe_name}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    }
    return StreamingResponse(iter_decrypted(path), media_type=registration.mime_type, headers=headers)


@router.get("/{identifier}/certificate")
def download_certificate(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, identifier)
    require_registration_access(user, registration, db)
    owner = db.get(User, registration.user_id)
    pdf = build_registration_certificate(
        registration,
        owner.display_name if owner else "AUTHENTIQ Creator",
        verification_url_for(registration.registration_id),
    )
    append_audit(
        db,
        "certificate_downloaded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="AUTHENTIQ-{registration.registration_id}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{identifier}/trust-score")
def get_trust_score(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, identifier)
    require_registration_access(user, registration, db)
    metadata = db.execute(
        select(FileMetadata).where(FileMetadata.registration_id == registration.id)
    ).scalar_one_or_none()
    return trust_report(db, registration, metadata)


@router.get("/{identifier}/evidence-packet")
def download_evidence_packet(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, identifier)
    require_registration_access(user, registration, db)
    metadata = db.execute(
        select(FileMetadata).where(FileMetadata.registration_id == registration.id)
    ).scalar_one_or_none()
    owner = db.get(User, registration.user_id)
    proofs = db.execute(
        select(ZkpProof).where(ZkpProof.registration_id == registration.id).order_by(ZkpProof.created_at.desc())
    ).scalars().all()
    packet = build_evidence_packet(
        db,
        registration,
        metadata,
        owner.display_name if owner else "AUTHENTIQ Creator",
        proofs,
    )
    append_audit(
        db,
        "evidence_packet_downloaded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"bytes": len(packet)},
    )
    db.commit()
    return Response(
        content=packet,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="AUTHENTIQ-{registration.registration_id}-evidence.zip"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{identifier}/verification-state")
def verification_state(identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, identifier)
    require_registration_access(user, registration, db)
    proofs = db.execute(
        select(ZkpProof).where(ZkpProof.registration_id == registration.id).order_by(ZkpProof.created_at.desc()).limit(10)
    ).scalars().all()
    ledger = ledger_service.verify_record(registration.ledger_tx_id) if registration.ledger_tx_id else None
    return {
        "registration_id": registration.registration_id,
        "fingerprint": registration.sha256,
        "commitment": registration.commitment,
        "ledger_tx_id": registration.ledger_tx_id,
        "ledger_mode": registration.ledger_mode,
        "ledger_record": ledger,
        "proofs": [
            {
                "id": proof.id,
                "scheme": proof.scheme,
                "status": proof.status,
                "created_at": proof.created_at.isoformat(),
                "verified_at": proof.verified_at.isoformat() if proof.verified_at else None,
            }
            for proof in proofs
        ],
    }
