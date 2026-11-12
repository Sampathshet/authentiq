"""Ownership state and append-only chain of ownership for registrations.

A registration can be in three states relative to the signed-in user:

* ``owned`` - the user is the recorded owner.
* ``pending_confirmation`` - an incoming transfer exists that the current
  owner still has to confirm. The recipient can read the record and its file
  data, but owner-only actions stay locked.
* ``not_owner`` - the user has no access through ownership.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Commitment, OwnershipTransfer, Registration, User
from app.services.access import PENDING_TRANSFER_STATUSES, is_registration_owner, pending_transfer_for
from app.services.serializers import iso


def pending_registration_ids(db: Session, user) -> set[str]:
    """Registration ids where the user is the incoming recipient of a pending transfer."""
    if not user or not getattr(user, "id", None):
        return set()
    rows = db.execute(
        select(OwnershipTransfer.registration_id).where(
            OwnershipTransfer.to_user_id == user.id,
            OwnershipTransfer.status.in_(PENDING_TRANSFER_STATUSES),
        )
    ).scalars().all()
    return set(rows)


def _user_names(db: Session, user_ids) -> dict[str, str]:
    ids = {item for item in user_ids if item}
    if not ids:
        return {}
    users = db.execute(select(User).where(User.id.in_(ids))).scalars().all()
    return {user.id: user.display_name for user in users}


def transfers_for(db: Session, registration) -> list[OwnershipTransfer]:
    return list(
        db.execute(
            select(OwnershipTransfer)
            .where(OwnershipTransfer.registration_id == registration.id)
            .order_by(OwnershipTransfer.created_at.asc())
        ).scalars().all()
    )


def ownership_state(db: Session, registration, user) -> dict:
    """Describe who owns the record and how the viewer is related to it."""
    transfers = transfers_for(db, registration)
    pending = pending_transfer_for(db, registration, user)
    owner = db.get(User, registration.user_id)
    names = _user_names(
        db,
        [registration.user_id]
        + [transfer.from_user_id for transfer in transfers]
        + [transfer.to_user_id for transfer in transfers],
    )
    completed = [transfer for transfer in transfers if transfer.status == "completed"]
    last_completed = completed[-1] if completed else None
    original_owner_id = transfers[0].from_user_id if transfers else registration.user_id
    commitment_versions = db.execute(
        select(Commitment).where(Commitment.registration_id == registration.id)
    ).scalars().all()

    if is_registration_owner(user, registration):
        status = "owned"
    elif pending is not None:
        status = "pending_confirmation"
    else:
        status = "not_owner"

    return {
        "status": status,
        "is_owner": status == "owned",
        "current_owner_id": registration.user_id,
        "current_owner_name": names.get(registration.user_id) or (owner.display_name if owner else None),
        "original_owner_id": original_owner_id,
        "original_owner_name": names.get(original_owner_id),
        "previous_owner_name": names.get(transfers[-1].from_user_id) if transfers else None,
        "transfer_count": len(transfers),
        "acquired_via_transfer_id": last_completed.id if last_completed else None,
        "acquired_at": iso(last_completed.completed_at) if last_completed else None,
        "pending_transfer": (
            {
                "id": pending.id,
                "status": pending.status,
                "from_name": names.get(pending.from_user_id),
                "from_id": pending.from_user_id,
                "to_email": pending.to_email,
                "reason": pending.reason,
                "created_at": iso(pending.created_at),
                "recipient_responded_at": iso(pending.recipient_responded_at),
                "awaiting": "owner_confirmation" if pending.status == "recipient_accepted" else "recipient_response",
            }
            if pending is not None
            else None
        ),
        "credential_rotations": max(0, len(commitment_versions) - 1),
        "credential_version": len(commitment_versions),
    }


def ownership_chain(db: Session, registration) -> dict:
    """Full append-only chain of ownership for a registration."""
    transfers = transfers_for(db, registration)
    names = _user_names(
        db,
        [registration.user_id]
        + [transfer.from_user_id for transfer in transfers]
        + [transfer.to_user_id for transfer in transfers],
    )
    original_owner_id = transfers[0].from_user_id if transfers else registration.user_id
    current_owner = db.get(User, registration.user_id)

    events: list[dict] = [
        {
            "kind": "registered",
            "owner_id": original_owner_id,
            "owner_name": names.get(original_owner_id),
            "at": iso(registration.registered_at),
            "status": "registered",
            "detail": "Creation registered and committed to the ledger.",
            "ledger_tx_id": registration.ledger_tx_id,
        }
    ]
    for transfer in transfers:
        events.append(
            {
                "kind": "transfer",
                "id": transfer.id,
                "status": transfer.status,
                "from_id": transfer.from_user_id,
                "from_name": names.get(transfer.from_user_id),
                "to_id": transfer.to_user_id,
                "to_name": names.get(transfer.to_user_id),
                "to_email": transfer.to_email,
                "reason": transfer.reason,
                "created_at": iso(transfer.created_at),
                "recipient_responded_at": iso(transfer.recipient_responded_at),
                "owner_confirmed_at": iso(transfer.owner_confirmed_at),
                "completed_at": iso(transfer.completed_at),
                "ledger_tx_id": transfer.ledger_tx_id,
                "is_current": transfer.status == "completed" and transfer.to_user_id == registration.user_id,
            }
        )

    return {
        "registration_id": registration.registration_id,
        "current_owner_id": registration.user_id,
        "current_owner_name": current_owner.display_name if current_owner else None,
        "events": events,
        "append_only": True,
        "note": "Ownership history is append-only. Completed transfers move the recorded owner and rotate the private ownership credential.",
    }
