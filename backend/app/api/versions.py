from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ledger import ledger_service
from app.models import CreativeVersion, FileMetadata, Registration, Upload, User
from app.schemas.content import VersionCreateRequest
from app.services.access import registration_or_404, require_registration_access, require_registration_owner
from app.services.audit import append_audit
from app.services.certificate import build_registration_certificate, verification_url_for
from app.services.notifications import notify
from app.services.serializers import version_out
from app.storage.files import iter_decrypted
from app.storage.scanner import scan_path
from app.core.config import settings

router = APIRouter(prefix="/versions", tags=["creative history"])


def _version_or_404(db: Session, version_id: str) -> CreativeVersion:
    version = db.get(CreativeVersion, version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version


@router.post("", status_code=status.HTTP_201_CREATED)
def create_version(
    payload: VersionCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    require_registration_owner(user, registration, db)
    upload = db.get(Upload, payload.upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    if upload.status != "completed" or not upload.final_sha256:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload must be completed first")
    duplicate = db.execute(
        select(CreativeVersion).where(
            CreativeVersion.registration_id == registration.id,
            CreativeVersion.sha256 == upload.final_sha256,
        )
    ).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Version {duplicate.version_no} already has this fingerprint")
    scan = scan_path(upload.filename, Path(upload.storage_path), settings.allowed_extension_list)
    if not scan["clean"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": "File rejected by scanner", "threats": scan["threats"]})
    latest = db.execute(
        select(CreativeVersion).where(CreativeVersion.registration_id == registration.id).order_by(CreativeVersion.version_no.desc()).limit(1)
    ).scalar_one_or_none()
    version = CreativeVersion(
        registration_id=registration.id,
        version_no=(latest.version_no + 1) if latest else 2,
        file_name=upload.filename,
        file_size=upload.size_bytes,
        mime_type=upload.mime_type,
        sha256=upload.final_sha256,
        storage_path=upload.storage_path,
        change_description=payload.change_description,
        contributor_id=user.id,
        parent_version_id=latest.id if latest else None,
    )
    db.add(version)
    db.flush()
    tx = ledger_service.record_version(db, user.id, registration, version)
    version.ledger_tx_id = tx.tx_id
    registration.version = max(registration.version, version.version_no)
    append_audit(
        db,
        "version_registered",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={
            "version_no": version.version_no,
            "sha256": version.sha256,
            "parent_version_id": version.parent_version_id,
            "ledger_tx_id": version.ledger_tx_id,
        },
    )
    notify(
        db,
        registration.user_id,
        "version",
        "New creative version recorded",
        f"Version {version.version_no} was added to {registration.registration_id}.",
        "registration",
        registration.id,
    )
    db.commit()
    return version_out(version, user.display_name)


@router.get("/registration/{registration_id}")
def list_versions(
    registration_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, registration_id)
    require_registration_access(user, registration, db)
    versions = db.execute(
        select(CreativeVersion)
        .where(CreativeVersion.registration_id == registration.id)
        .order_by(CreativeVersion.version_no.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    contributor_ids = {version.contributor_id for version in versions}
    names = {
        contributor.id: contributor.display_name
        for contributor in db.execute(select(User).where(User.id.in_(contributor_ids))).scalars().all()
    } if contributor_ids else {}
    return {
        "registration": {
            "id": registration.id,
            "registration_id": registration.registration_id,
            "title": registration.title,
            "sha256": registration.sha256,
            "current_version": registration.version,
        },
        "items": [version_out(version, names.get(version.contributor_id)) for version in versions],
        "page": page,
        "page_size": page_size,
    }


@router.get("/compare")
def compare_versions(
    left: str,
    right: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    left_version = _version_or_404(db, left)
    right_version = _version_or_404(db, right)
    if left_version.registration_id != right_version.registration_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Versions must belong to the same registration")
    registration = db.get(Registration, left_version.registration_id)
    require_registration_access(user, registration, db)
    return {
        "same_fingerprint": left_version.sha256 == right_version.sha256,
        "left": version_out(left_version),
        "right": version_out(right_version),
        "differences": {
            "file_name": left_version.file_name != right_version.file_name,
            "file_size": left_version.file_size != right_version.file_size,
            "sha256": left_version.sha256 != right_version.sha256,
            "version_no": left_version.version_no != right_version.version_no,
        },
    }


@router.get("/{version_id}")
def get_version(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    version = _version_or_404(db, version_id)
    registration = db.get(Registration, version.registration_id)
    require_registration_access(user, registration, db)
    contributor = db.get(User, version.contributor_id)
    payload = version_out(version, contributor.display_name if contributor else None)
    payload["registration_label"] = registration.registration_id
    return payload


@router.get("/{version_id}/file")
def download_version(
    version_id: str,
    inline: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    version = _version_or_404(db, version_id)
    registration = db.get(Registration, version.registration_id)
    require_registration_access(user, registration, db)
    path = Path(version.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Stored version file is unavailable")
    return StreamingResponse(
        iter_decrypted(path),
        media_type=version.mime_type,
        headers={
            "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{version.file_name.replace(chr(34), "")}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{version_id}/certificate")
def version_certificate(version_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    version = _version_or_404(db, version_id)
    registration = db.get(Registration, version.registration_id)
    require_registration_access(user, registration, db)
    contributor = db.get(User, version.contributor_id)
    shim = SimpleNamespace(
        registration_id=f"{registration.registration_id}-V{version.version_no}",
        file_name=version.file_name,
        sha256=version.sha256,
        commitment=registration.commitment,
        poseidon_commitment=registration.poseidon_commitment,
        registered_at=version.created_at,
        ledger_tx_id=version.ledger_tx_id,
        ledger_mode=registration.ledger_mode,
    )
    pdf = build_registration_certificate(
        shim,
        contributor.display_name if contributor else "AUTHENTIQ Creator",
        verification_url_for(registration.registration_id),
    )
    append_audit(
        db,
        "version_certificate_downloaded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"version_no": version.version_no},
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AUTHENTIQ-{registration.registration_id}-V{version.version_no}.pdf"'},
    )
