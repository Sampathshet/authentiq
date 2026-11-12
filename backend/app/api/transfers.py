from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ledger import ledger_service
from app.models import Commitment, Organization, OwnershipTransfer, Registration, User
from app.schemas.content import TransferCreateRequest, TransferDecisionRequest
from app.security.crypto import encrypt_text, utcnow
from app.services.access import registration_or_404, require_registration_access
from app.services.audit import append_audit
from app.services.notifications import notify
from app.services.serializers import transfer_out
from app.zkp.sigma import create_commitment

router = APIRouter(prefix="/transfers", tags=["ownership transfer"])


def _transfer_or_404(db: Session, transfer_id: str) -> OwnershipTransfer:
    transfer = db.get(OwnershipTransfer, transfer_id)
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer request not found")
    return transfer


def _ensure_party(transfer: OwnershipTransfer, user: User, allow_recipient: bool = True, allow_owner: bool = True):
    is_owner = transfer.from_user_id == user.id
    is_recipient = transfer.to_user_id == user.id
    if (allow_owner and is_owner) or (allow_recipient and is_recipient):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized for this transfer")


def _serialize(db: Session, transfer: OwnershipTransfer, registration: Registration | None = None) -> dict:
    registration = registration or db.get(Registration, transfer.registration_id)
    from_user = db.get(User, transfer.from_user_id)
    to_user = db.get(User, transfer.to_user_id) if transfer.to_user_id else None
    return transfer_out(
        transfer,
        registration,
        from_user.display_name if from_user else None,
        to_user.display_name if to_user else None,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransferCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    if registration.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the current owner can create a transfer")
    try:
        recipient_email = validate_email(payload.recipient_email, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if recipient_email == user.email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="You cannot transfer ownership to yourself")
    recipient = db.execute(select(User).where(User.email == recipient_email)).scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient must have an AUTHENTIQ account before a transfer can be proposed")
    pending = db.execute(
        select(OwnershipTransfer).where(
            OwnershipTransfer.registration_id == registration.id,
            OwnershipTransfer.status.in_(["pending_recipient", "recipient_accepted"]),
        )
    ).scalar_one_or_none()
    if pending:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A transfer for this registration is already in progress")
    organization = None
    if payload.to_organization_id:
        organization = db.get(Organization, payload.to_organization_id)
        if not organization:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination organization not found")
        if recipient.organization_id != organization.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Recipient must belong to the destination organization")
    transfer = OwnershipTransfer(
        registration_id=registration.id,
        from_user_id=user.id,
        to_user_id=recipient.id,
        to_email=recipient.email,
        to_organization_id=organization.id if organization else None,
        reason=payload.reason,
        status="pending_recipient",
    )
    db.add(transfer)
    db.flush()
    notify(
        db,
        recipient.id,
        "transfer",
        "Ownership transfer requested",
        f"{user.display_name} proposed transferring {registration.registration_id} to you.",
        "transfer",
        transfer.id,
    )
    append_audit(
        db,
        "transfer_requested",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"transfer_id": transfer.id, "to_user_id": recipient.id},
    )
    db.commit()
    return _serialize(db, transfer, registration)


@router.get("")
def list_transfers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    direction: str = Query(default="all", pattern="^(all|outgoing|incoming)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filters = []
    if direction == "outgoing":
        filters.append(OwnershipTransfer.from_user_id == user.id)
    elif direction == "incoming":
        filters.append(OwnershipTransfer.to_user_id == user.id)
    else:
        filters.append(or_(OwnershipTransfer.from_user_id == user.id, OwnershipTransfer.to_user_id == user.id))
    query = select(OwnershipTransfer).where(*filters)
    if status_filter:
        query = query.where(OwnershipTransfer.status == status_filter)
    transfers = db.execute(
        query.order_by(OwnershipTransfer.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {"items": [_serialize(db, transfer) for transfer in transfers], "page": page, "page_size": page_size}


@router.get("/history/{registration_id}")
def transfer_history(registration_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registration = registration_or_404(db, registration_id)
    require_registration_access(user, registration, db)
    transfers = db.execute(
        select(OwnershipTransfer)
        .where(OwnershipTransfer.registration_id == registration.id)
        .order_by(OwnershipTransfer.created_at.asc())
    ).scalars().all()
    return {
        "registration": {
            "registration_id": registration.registration_id,
            "title": registration.title,
            "current_owner_id": registration.user_id,
        },
        "items": [_serialize(db, transfer, registration) for transfer in transfers],
        "chain_of_ownership_is_append_only": True,
    }


@router.post("/{transfer_id}/accept")
def accept_transfer(
    transfer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    transfer = _transfer_or_404(db, transfer_id)
    _ensure_party(transfer, user, allow_recipient=True, allow_owner=False)
    if transfer.status != "pending_recipient":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transfer is not awaiting recipient acceptance")
    transfer.status = "recipient_accepted"
    transfer.recipient_responded_at = utcnow()
    notify(
        db,
        transfer.from_user_id,
        "transfer",
        "Transfer accepted by recipient",
        f"{user.display_name} accepted the transfer. Confirm to finalize ownership.",
        "transfer",
        transfer.id,
    )
    append_audit(
        db,
        "transfer_recipient_accepted",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="transfer",
        entity_id=transfer.id,
    )
    db.commit()
    return _serialize(db, transfer)


@router.post("/{transfer_id}/reject")
def reject_transfer(
    transfer_id: str,
    payload: TransferDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    transfer = _transfer_or_404(db, transfer_id)
    _ensure_party(transfer, user, allow_recipient=True, allow_owner=False)
    if transfer.status not in {"pending_recipient", "recipient_accepted"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transfer cannot be rejected in its current state")
    transfer.status = "rejected"
    transfer.rejection_reason = payload.reason
    transfer.recipient_responded_at = utcnow()
    notify(
        db,
        transfer.from_user_id,
        "transfer",
        "Transfer rejected",
        f"{user.display_name} rejected the ownership transfer request.",
        "transfer",
        transfer.id,
    )
    append_audit(
        db,
        "transfer_rejected",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="transfer",
        entity_id=transfer.id,
        metadata={"reason": payload.reason},
    )
    db.commit()
    return _serialize(db, transfer)


@router.post("/{transfer_id}/cancel")
def cancel_transfer(transfer_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    transfer = _transfer_or_404(db, transfer_id)
    _ensure_party(transfer, user, allow_recipient=False, allow_owner=True)
    if transfer.status not in {"pending_recipient", "recipient_accepted"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transfer cannot be cancelled in its current state")
    transfer.status = "cancelled"
    if transfer.to_user_id:
        notify(
            db,
            transfer.to_user_id,
            "transfer",
            "Transfer cancelled",
            "The owner cancelled the pending ownership transfer.",
            "transfer",
            transfer.id,
        )
    append_audit(db, "transfer_cancelled", actor_id=user.id, actor_ref=user.email, entity_type="transfer", entity_id=transfer.id)
    db.commit()
    return _serialize(db, transfer)


@router.post("/{transfer_id}/confirm")
def confirm_transfer(
    transfer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    transfer = _transfer_or_404(db, transfer_id)
    _ensure_party(transfer, user, allow_recipient=False, allow_owner=True)
    if transfer.status != "recipient_accepted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recipient must accept before the owner confirms")
    registration = db.get(Registration, transfer.registration_id)
    if not registration or registration.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are no longer the owner of this registration")
    recipient = db.get(User, transfer.to_user_id)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient account no longer exists")
    registration.user_id = recipient.id
    registration.organization_id = transfer.to_organization_id if transfer.to_organization_id else None
    transfer.status = "completed"
    transfer.owner_confirmed_at = utcnow()
    transfer.completed_at = utcnow()

    previous_commitment = registration.commitment
    rotated = create_commitment(registration.sha256)
    registration.commitment = rotated["pedersen_commitment"]
    registration.poseidon_commitment = rotated["poseidon_commitment"]
    registration.secret_encrypted = encrypt_text(format(rotated["secret_int"], "064x"))
    registration.blinding_encrypted = encrypt_text(format(rotated["blinding_int"], "064x"))
    db.add(
        Commitment(
            registration_id=registration.id,
            scheme=rotated["scheme"],
            commitment_hex=rotated["pedersen_commitment"],
            poseidon_hex=rotated["poseidon_commitment"],
            fingerprint=registration.sha256,
        )
    )
    db.flush()

    tx = ledger_service.transfer_ownership(db, user.id, registration, transfer)
    transfer.ledger_tx_id = tx.tx_id
    rotation_tx = ledger_service.record_credential_rotation(
        db,
        user.id,
        registration,
        transfer,
        previous_commitment,
        rotated["pedersen_commitment"],
    )
    notify(
        db,
        recipient.id,
        "transfer",
        "Ownership transfer completed",
        f"You are now the recorded owner of {registration.registration_id}. The private verification key was rotated with the ownership - reveal it from the record.",
        "registration",
        registration.id,
    )
    append_audit(
        db,
        "transfer_completed",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={
            "transfer_id": transfer.id,
            "to_user_id": recipient.id,
            "ledger_tx_id": transfer.ledger_tx_id,
            "credential_rotated": True,
            "rotation_tx_id": rotation_tx.tx_id,
        },
    )
    append_audit(
        db,
        "ownership_credential_rotated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={
            "transfer_id": transfer.id,
            "previous_commitment": previous_commitment,
            "new_commitment": rotated["pedersen_commitment"],
        },
    )
    db.commit()
    payload = _serialize(db, transfer, registration)
    payload["credential_rotated"] = True
    payload["new_owner_id"] = recipient.id
    payload["new_owner_name"] = recipient.display_name
    return payload
