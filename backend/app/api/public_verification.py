"""Public, login-free anonymous ownership verification.

Flow:
1. The verifier supplies the registration reference and the SHA-256 of the
   original file (hashed locally in the browser).
2. The server checks the fingerprint and issues a single-use challenge.
3. The browser generates a BN254 Schnorr proof locally from the creator's
   private verification key. The key itself is never transmitted.
4. The server verifies the proof and returns a checklist. No account or
   session is involved.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import client_ip
from app.ledger import ledger_service
from app.models import Registration, ZkpChallenge, ZkpProof
from app.schemas.content import (
    AnonymousChallengeRequest,
    AnonymousProofVerifyRequest,
    PublicFingerprintCheckRequest,
)
from app.security.crypto import constant_time_compare, random_url_token, utcnow
from app.security.rate_limit import proof_limiter
from app.services.audit import append_audit
from app.services.notifications import notify
from app.zkp.sigma import SIGMA_SCHEME, public_signals, verify_proof

router = APIRouter(prefix="/public/verify/anonymous", tags=["anonymous verification"])
public_fingerprints = APIRouter(prefix="/public/fingerprints", tags=["public verification"])

STATEMENT = (
    "The verifier proves knowledge of the opening of the registered ownership commitment "
    "without disclosing the private credential. The SHA-256 fingerprint of the supplied file "
    "is compared against the registered record before a challenge is issued."
)


def _aware(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=utcnow().tzinfo)
    return value


def _registration_by_reference(db: Session, reference: str) -> Registration | None:
    reference = (reference or "").strip()
    if not reference:
        return None
    return db.execute(
        select(Registration).where(Registration.registration_id == reference)
    ).scalar_one_or_none()


@router.post("/challenge")
def anonymous_challenge(
    payload: AnonymousChallengeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = client_ip(request)
    allowed, retry_after = proof_limiter.check(f"anon-challenge:{ip}", 30, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many verification attempts. Retry in {retry_after} seconds.",
        )

    registration = _registration_by_reference(db, payload.registration_id)
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registration exists for that reference ID",
        )
    if not constant_time_compare(registration.sha256, payload.file_sha256.lower()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file fingerprint does not match the registered creation",
        )

    previous = db.execute(
        select(ZkpChallenge).where(
            ZkpChallenge.registration_id == registration.id,
            ZkpChallenge.purpose == "anonymous",
            ZkpChallenge.used_at.is_(None),
        )
    ).scalars().all()
    for item in previous:
        item.used_at = utcnow()

    challenge = ZkpChallenge(
        registration_id=registration.id,
        user_id=registration.user_id,
        nonce=random_url_token(32),
        purpose="anonymous",
        expires_at=utcnow() + timedelta(minutes=settings.zkp_challenge_minutes),
    )
    db.add(challenge)
    db.flush()
    append_audit(
        db,
        "anonymous_challenge_created",
        actor_id=None,
        actor_ref="anonymous verifier",
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"challenge_id": challenge.id, "ip": ip},
        ip_address=ip,
    )
    db.commit()

    return {
        "challenge_id": challenge.id,
        "nonce": challenge.nonce,
        "expires_at": challenge.expires_at.isoformat(),
        "registration_id": registration.registration_id,
        "fingerprint": registration.sha256,
        "commitment": registration.commitment,
        "poseidon_commitment": registration.poseidon_commitment,
        "proof_system": SIGMA_SCHEME,
        "statement": STATEMENT,
        "challenge_minutes": settings.zkp_challenge_minutes,
    }


@router.post("/verify")
def anonymous_verify(
    payload: AnonymousProofVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = client_ip(request)
    allowed, retry_after = proof_limiter.check(f"anon-verify:{ip}", 30, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many verification attempts. Retry in {retry_after} seconds.",
        )

    challenge = db.get(ZkpChallenge, payload.challenge_id)
    if not challenge or challenge.purpose != "anonymous":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    if challenge.used_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Challenge has already been used")
    if _aware(challenge.expires_at) < utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Challenge has expired. Request a new one.")

    registration = db.get(Registration, challenge.registration_id)
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration no longer exists")

    challenge.used_at = utcnow()
    valid, message = verify_proof(
        payload.proof,
        registration.sha256,
        registration.registration_id,
        challenge.nonce,
        registration.commitment,
    )
    stated = payload.proof.get("public_signals") or {}
    expected_signals = public_signals(
        registration.sha256,
        registration.registration_id,
        challenge.nonce,
        registration.commitment,
    )
    signals_match = (
        stated.get("fingerprint") == registration.sha256
        and stated.get("registration_id") == registration.registration_id
        and stated.get("challenge_nonce") == challenge.nonce
        and stated.get("commitment") == registration.commitment
    )
    if valid and not signals_match:
        valid, message = False, "Public signals do not match the registered record"

    record = ZkpProof(
        registration_id=registration.id,
        user_id=registration.user_id,
        challenge_id=challenge.id,
        scheme=payload.proof.get("scheme", SIGMA_SCHEME),
        public_signals=stated or expected_signals,
        proof=payload.proof,
        status="verified" if valid else "invalid",
        verified_at=utcnow() if valid else None,
    )
    db.add(record)
    db.flush()

    if valid:
        registration.verified_at = utcnow()
        if registration.status == "registered":
            registration.status = "verified"
        ledger_service.record_proof_verification(db, registration.user_id, record, registration)
        notify(
            db,
            registration.user_id,
            "proof",
            "Anonymous ownership verification succeeded",
            f"A verifier confirmed ownership of {registration.registration_id} without signing in.",
            "registration",
            registration.id,
        )
    append_audit(
        db,
        "anonymous_proof_verified" if valid else "anonymous_proof_verification_failed",
        actor_id=None,
        actor_ref="anonymous verifier",
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"valid": valid, "message": message, "proof_id": record.id, "ip": ip},
        ip_address=ip,
    )
    db.commit()

    return {
        "valid": valid,
        "message": message,
        "registration_id": registration.registration_id,
        "proof_system": payload.proof.get("scheme", SIGMA_SCHEME),
        "verified_at": utcnow().isoformat() if valid else None,
        "statement": STATEMENT,
        "checks": {
            "registration_exists": True,
            "file_fingerprint_matches": True,
            "challenge_valid": True,
            "proof_valid": valid,
            "private_key_disclosed": False,
            "login_required": False,
        },
        "public_record": {
            "fingerprint": registration.sha256,
            "commitment": registration.commitment,
            "registered_at": registration.registered_at.isoformat() if registration.registered_at else None,
            "ledger_tx_id": registration.ledger_tx_id,
            "ledger_mode": registration.ledger_mode,
        },
    }


@public_fingerprints.post("/check")
def public_fingerprint_check(
    payload: PublicFingerprintCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public existence check for a SHA-256 fingerprint.

    Returns only whether the fingerprint is registered and how many records
    hold it. No owner, title, or registration reference is disclosed.
    """
    ip = client_ip(request)
    allowed, retry_after = proof_limiter.check(f"public-fingerprint:{ip}", 120, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many fingerprint checks. Retry in {retry_after} seconds.",
        )
    fingerprint = payload.sha256.lower()
    total = db.execute(
        select(func.count()).select_from(Registration).where(Registration.sha256 == fingerprint)
    ).scalar_one()
    return {
        "sha256": fingerprint,
        "registered": total > 0,
        "records": total,
        "note": "Existence only. Proving the private ownership claim requires the creator's verification key.",
    }
