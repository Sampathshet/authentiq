import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.ledger import ledger_service
from app.models import (
    AuditLog,
    CreativeVersion,
    Dispute,
    DisputeEvidence,
    OwnershipTransfer,
    Registration,
    User,
    ZkpProof,
)
from app.schemas.content import DisputeCreateRequest, DisputeStatusRequest
from app.security.crypto import sha256_hex, utcnow
from app.services.access import registration_or_404, require_registration_access
from app.services.audit import append_audit, verify_audit_chain
from app.services.notifications import notify
from app.services.serializers import dispute_out
from app.storage.files import encrypt_file_to, iter_decrypted
from app.storage.scanner import scan_bytes

router = APIRouter(prefix="/disputes", tags=["dispute resolution"])


def _dispute_or_404(db: Session, dispute_id: str) -> Dispute:
    dispute = db.get(Dispute, dispute_id)
    if not dispute:
        dispute = db.execute(select(Dispute).where(Dispute.dispute_ref == dispute_id)).scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    return dispute


def _is_reviewer(user: User, registration: Registration | None) -> bool:
    if user.role == "verifier":
        return True
    if user.role == "org_admin" and registration and user.organization_id == registration.organization_id:
        return True
    return False


def _can_view(db: Session, dispute: Dispute, registration: Registration, user: User) -> bool:
    return (
        dispute.claimant_id == user.id
        or dispute.respondent_id == user.id
        or _is_reviewer(user, registration)
    )


def _require_view(db: Session, dispute: Dispute, user: User) -> Registration:
    registration = db.get(Registration, dispute.registration_id)
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disputed registration not found")
    if not _can_view(db, dispute, registration, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this dispute")
    return registration


def _new_ref() -> str:
    return f"DSP-{utcnow().year}-{secrets.token_hex(3).upper()}"


@router.post("", status_code=status.HTTP_201_CREATED)
def create_dispute(
    payload: DisputeCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    duplicate = db.execute(
        select(Dispute).where(
            Dispute.registration_id == registration.id,
            Dispute.claimant_id == user.id,
            Dispute.status.in_(["open", "under_review", "evidence_requested"]),
        )
    ).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an active dispute for this registration")
    same_fingerprint = db.execute(
        select(Registration)
        .where(Registration.sha256 == registration.sha256)
        .order_by(Registration.registered_at.asc())
    ).scalars().all()
    earliest = same_fingerprint[0] if same_fingerprint else registration
    dispute = Dispute(
        dispute_ref=_new_ref(),
        registration_id=registration.id,
        claimant_id=user.id,
        respondent_id=registration.user_id,
        reason=payload.reason,
        description=payload.description,
        status="open",
        earliest_registration_id=earliest.registration_id,
        is_demo=user.is_demo,
    )
    db.add(dispute)
    db.flush()
    ledger_service.record_dispute(db, user.id, dispute)
    if registration.user_id != user.id:
        notify(
            db,
            registration.user_id,
            "dispute",
            "New ownership dispute",
            f"A dispute was opened for {registration.registration_id}. Review the evidence report.",
            "dispute",
            dispute.id,
        )
    notify(
        db,
        user.id,
        "dispute",
        "Dispute submitted",
        f"Dispute {dispute.dispute_ref} was opened. The evidence report is available.",
        "dispute",
        dispute.id,
    )
    append_audit(
        db,
        "dispute_submitted",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="dispute",
        entity_id=dispute.dispute_ref,
        metadata={"registration_id": registration.registration_id, "earliest_registration": earliest.registration_id},
    )
    db.commit()
    return dispute_out(dispute, registration, user.display_name)


@router.get("")
def list_disputes(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    if user.role == "verifier":
        query = select(Dispute)
    else:
        query = select(Dispute).where(or_(Dispute.claimant_id == user.id, Dispute.respondent_id == user.id))
    if status_filter:
        query = query.where(Dispute.status == status_filter)
    disputes = db.execute(
        query.order_by(Dispute.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    result = []
    for dispute in disputes:
        registration = db.get(Registration, dispute.registration_id)
        claimant = db.get(User, dispute.claimant_id)
        result.append(dispute_out(dispute, registration, claimant.display_name if claimant else None))
    return {"items": result, "page": page, "page_size": page_size}


@router.get("/{dispute_id}")
def get_dispute(dispute_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dispute = _dispute_or_404(db, dispute_id)
    registration = _require_view(db, dispute, user)
    claimant = db.get(User, dispute.claimant_id)
    respondent = db.get(User, dispute.respondent_id) if dispute.respondent_id else None
    evidence = db.execute(
        select(DisputeEvidence).where(DisputeEvidence.dispute_id == dispute.id).order_by(DisputeEvidence.created_at.desc())
    ).scalars().all()
    payload = dispute_out(dispute, registration, claimant.display_name if claimant else None)
    payload["registration"] = {
        "registration_id": registration.registration_id,
        "title": registration.title,
        "sha256": registration.sha256,
        "registered_at": registration.registered_at.isoformat(),
        "ledger_tx_id": registration.ledger_tx_id,
        "ledger_mode": registration.ledger_mode,
        "owner_id": registration.user_id,
    }
    payload["respondent_name"] = respondent.display_name if respondent else None
    payload["evidence"] = [
        {
            "id": item.id,
            "file_name": item.file_name,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
            "description": item.description,
            "uploaded_by": item.uploaded_by,
            "created_at": item.created_at.isoformat(),
        }
        for item in evidence
    ]
    payload["can_review"] = _is_reviewer(user, registration)
    payload["can_upload_evidence"] = dispute.claimant_id == user.id or dispute.respondent_id == user.id or _is_reviewer(user, registration)
    return payload


@router.post("/{dispute_id}/evidence", status_code=status.HTTP_201_CREATED)
def upload_evidence(
    dispute_id: str,
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dispute = _dispute_or_404(db, dispute_id)
    registration = _require_view(db, dispute, user)
    data = file.file.read(settings.max_file_size_bytes + 1)
    if len(data) > settings.max_file_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Evidence file is too large")
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Evidence file is empty")
    filename = (file.filename or "evidence.bin").replace("\\", "/").split("/")[-1][:300]
    scan = scan_bytes(filename, data, settings.allowed_extension_list)
    if not scan["clean"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": "Evidence rejected by scanner", "threats": scan["threats"]})
    evidence_dir = settings.evidence_dir / dispute.id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    temp_path = evidence_dir / f"{secrets.token_hex(8)}.tmp"
    temp_path.write_bytes(data)
    destination = evidence_dir / f"{secrets.token_hex(16)}.aqenc"
    encrypt_file_to(temp_path, destination)
    temp_path.unlink(missing_ok=True)
    evidence = DisputeEvidence(
        dispute_id=dispute.id,
        uploaded_by=user.id,
        file_name=filename,
        sha256=sha256_hex(data),
        size_bytes=len(data),
        storage_path=str(destination),
        description=(description or "")[:2000] or None,
    )
    db.add(evidence)
    counterpart = dispute.respondent_id if dispute.claimant_id == user.id else dispute.claimant_id
    if counterpart and counterpart != user.id:
        notify(
            db,
            counterpart,
            "dispute",
            "New dispute evidence",
            f"New evidence was attached to {dispute.dispute_ref}.",
            "dispute",
            dispute.id,
        )
    append_audit(
        db,
        "dispute_evidence_uploaded",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="dispute",
        entity_id=dispute.dispute_ref,
        metadata={"sha256": evidence.sha256, "size": evidence.size_bytes},
    )
    db.commit()
    return {"id": evidence.id, "sha256": evidence.sha256, "file_name": evidence.file_name}


@router.get("/{dispute_id}/evidence/{evidence_id}")
def download_evidence(
    dispute_id: str,
    evidence_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dispute = _dispute_or_404(db, dispute_id)
    _require_view(db, dispute, user)
    evidence = db.get(DisputeEvidence, evidence_id)
    if not evidence or evidence.dispute_id != dispute.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    path = Path(evidence.storage_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Evidence file is no longer available")
    return StreamingResponse(
        iter_decrypted(path),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{evidence.file_name.replace(chr(34), "")}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/{dispute_id}/status")
def update_status(
    dispute_id: str,
    payload: DisputeStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dispute = _dispute_or_404(db, dispute_id)
    registration = _require_view(db, dispute, user)
    reviewer = _is_reviewer(user, registration)
    if payload.status in {"resolved", "rejected"} and not reviewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an authorized verifier or organization admin can finalize a dispute")
    if payload.status in {"under_review", "evidence_requested"} and not (
        reviewer or dispute.claimant_id == user.id or dispute.respondent_id == user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to change this dispute")
    if payload.status in {"resolved", "rejected"} and not payload.resolution:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A resolution summary is required")
    dispute.status = payload.status
    if payload.resolution:
        dispute.resolution = payload.resolution
    if payload.status in {"resolved", "rejected"}:
        dispute.resolved_at = utcnow()
        if payload.status == "resolved":
            registration.status = "verified"
    recipients = [dispute.claimant_id, dispute.respondent_id]
    for recipient in recipients:
        if recipient:
            notify(
                db,
                recipient,
                "dispute",
                "Dispute status changed",
                f"Dispute {dispute.dispute_ref} is now {payload.status.replace('_', ' ')}.",
                "dispute",
                dispute.id,
            )
    append_audit(
        db,
        "dispute_status_changed",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="dispute",
        entity_id=dispute.dispute_ref,
        metadata={"status": dispute.status, "reviewer": reviewer},
    )
    db.commit()
    return {"message": "Dispute status updated", "status": dispute.status}


@router.get("/{dispute_id}/report")
def evidence_report(dispute_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dispute = _dispute_or_404(db, dispute_id)
    registration = _require_view(db, dispute, user)
    claimant = db.get(User, dispute.claimant_id)
    related = db.execute(
        select(Registration).where(Registration.sha256 == registration.sha256).order_by(Registration.registered_at.asc())
    ).scalars().all()
    related_ids = [item.id for item in related]
    owners = {
        owner.id: owner.display_name
        for owner in db.execute(select(User).where(User.id.in_({item.user_id for item in related}))).scalars().all()
    } if related else {}
    proofs = db.execute(
        select(ZkpProof).where(ZkpProof.registration_id.in_(related_ids)).order_by(ZkpProof.created_at.desc())
    ).scalars().all() if related_ids else []
    versions = db.execute(
        select(CreativeVersion).where(CreativeVersion.registration_id.in_(related_ids)).order_by(CreativeVersion.created_at.asc())
    ).scalars().all() if related_ids else []
    transfers = db.execute(
        select(OwnershipTransfer).where(OwnershipTransfer.registration_id.in_(related_ids)).order_by(OwnershipTransfer.created_at.asc())
    ).scalars().all() if related_ids else []
    evidence = db.execute(
        select(DisputeEvidence).where(DisputeEvidence.dispute_id == dispute.id).order_by(DisputeEvidence.created_at.asc())
    ).scalars().all()
    audit_entries = db.execute(
        select(AuditLog)
        .where(or_(AuditLog.entity_id == dispute.dispute_ref, AuditLog.entity_id.in_([item.registration_id for item in related])))
        .order_by(AuditLog.created_at.asc())
        .limit(300)
    ).scalars().all()
    earliest = related[0] if related else registration
    ledger_record = ledger_service.verify_record(registration.ledger_tx_id) if registration.ledger_tx_id else None
    report = {
        "format": "AUTHENTIQ-DISPUTE-EVIDENCE-REPORT-V1",
        "generated_at": utcnow().isoformat(),
        "dispute": {
            "dispute_ref": dispute.dispute_ref,
            "claimant_reference": claimant.display_name if claimant else dispute.claimant_id,
            "claimant_id": dispute.claimant_id,
            "reason": dispute.reason,
            "description": dispute.description,
            "status": dispute.status,
            "created_at": dispute.created_at.isoformat(),
        },
        "registration_records": [
            {
                "registration_id": item.registration_id,
                "owner_reference": owners.get(item.user_id, "unknown"),
                "sha256": item.sha256,
                "commitment": item.commitment,
                "registered_at": item.registered_at.isoformat(),
                "creation_timestamp": item.creation_timestamp.isoformat() if item.creation_timestamp else None,
                "ledger_tx_id": item.ledger_tx_id,
                "ledger_mode": item.ledger_mode,
                "status": item.status,
                "is_subject": item.id == registration.id,
            }
            for item in related
        ],
        "registration_priority": {
            "earliest_registration_id": earliest.registration_id,
            "earliest_registered_at": earliest.registered_at.isoformat(),
            "interpretation": "Earliest registration is displayed as registration priority evidence. It is not an automatic legal determination of authorship.",
        },
        "ledger": {
            "mode": registration.ledger_mode,
            "transaction": ledger_record,
            "chain_audit": ledger_service.audit(),
        },
        "proof_verification": {
            "total": len(proofs),
            "verified": len([proof for proof in proofs if proof.status == "verified"]),
            "items": [
                {
                    "registration_id": proof.registration_id,
                    "scheme": proof.scheme,
                    "status": proof.status,
                    "created_at": proof.created_at.isoformat(),
                    "verified_at": proof.verified_at.isoformat() if proof.verified_at else None,
                }
                for proof in proofs
            ],
        },
        "version_history": [
            {
                "registration_id": version.registration_id,
                "version_no": version.version_no,
                "sha256": version.sha256,
                "file_name": version.file_name,
                "change_description": version.change_description,
                "created_at": version.created_at.isoformat(),
                "ledger_tx_id": version.ledger_tx_id,
            }
            for version in versions
        ],
        "transfer_history": [
            {
                "registration_id": transfer.registration_id,
                "from_user_id": transfer.from_user_id,
                "to_user_id": transfer.to_user_id,
                "status": transfer.status,
                "created_at": transfer.created_at.isoformat(),
                "completed_at": transfer.completed_at.isoformat() if transfer.completed_at else None,
                "ledger_tx_id": transfer.ledger_tx_id,
            }
            for transfer in transfers
        ],
        "evidence": [
            {
                "file_name": item.file_name,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "description": item.description,
                "created_at": item.created_at.isoformat(),
            }
            for item in evidence
        ],
        "audit_trail": [
            {
                "event_id": entry.event_id,
                "action": entry.action,
                "actor_ref": entry.actor_ref,
                "entity_id": entry.entity_id,
                "created_at": entry.created_at.isoformat(),
                "record_hash": entry.record_hash,
            }
            for entry in audit_entries
        ],
        "audit_chain": verify_audit_chain(db),
        "limitations": "This report organizes cryptographic and registration evidence. It does not provide legal advice or automatically establish copyright ownership.",
    }
    append_audit(
        db,
        "dispute_report_generated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="dispute",
        entity_id=dispute.dispute_ref,
    )
    db.commit()
    return report
