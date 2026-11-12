"""One-off backfill: rotate ownership credentials for transfers completed before
the rotation feature existed.

Completed ownership transfers now rotate the private ownership credential so the
previous owner can no longer prove ownership. Transfers that were finalised
before this behaviour shipped kept the original commitment, which would leave
the previous owner able to prove ownership of a record they no longer own.

Run with:  python -m scripts.rotate_legacy_transfer_credentials
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.ledger import ledger_service
from app.models import Commitment, OwnershipTransfer, Registration
from app.security.crypto import encrypt_text, utcnow
from app.services.audit import append_audit
from app.zkp.sigma import create_commitment


def main() -> None:
    rotated = 0
    with SessionLocal() as db:
        transfers = db.execute(
            select(OwnershipTransfer).where(OwnershipTransfer.status == "completed")
        ).scalars().all()
        for transfer in transfers:
            registration = db.get(Registration, transfer.registration_id)
            if not registration or registration.user_id != transfer.to_user_id:
                continue
            existing = db.execute(
                select(Commitment).where(Commitment.registration_id == registration.id)
            ).scalars().all()
            if len(existing) > 1:
                continue

            previous_commitment = registration.commitment
            fresh = create_commitment(registration.sha256)
            registration.commitment = fresh["pedersen_commitment"]
            registration.poseidon_commitment = fresh["poseidon_commitment"]
            registration.secret_encrypted = encrypt_text(format(fresh["secret_int"], "064x"))
            registration.blinding_encrypted = encrypt_text(format(fresh["blinding_int"], "064x"))
            db.add(
                Commitment(
                    registration_id=registration.id,
                    scheme=fresh["scheme"],
                    commitment_hex=fresh["pedersen_commitment"],
                    poseidon_hex=fresh["poseidon_commitment"],
                    fingerprint=registration.sha256,
                )
            )
            db.flush()
            ledger_service.record_credential_rotation(
                db,
                transfer.to_user_id,
                registration,
                transfer,
                previous_commitment,
                fresh["pedersen_commitment"],
            )
            append_audit(
                db,
                "ownership_credential_rotated",
                actor_id=transfer.to_user_id,
                actor_ref="backfill",
                entity_type="registration",
                entity_id=registration.registration_id,
                metadata={
                    "transfer_id": transfer.id,
                    "previous_commitment": previous_commitment,
                    "new_commitment": fresh["pedersen_commitment"],
                    "reason": "backfill for transfers completed before credential rotation shipped",
                },
            )
            rotated += 1
            print(f"rotated credential for {registration.registration_id} (transfer {transfer.id})")
        db.commit()
    print(f"done: {rotated} credential(s) rotated")


if __name__ == "__main__":
    main()
