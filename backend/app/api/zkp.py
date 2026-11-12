from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.ledger import ledger_service
from app.models import Registration, User, ZkpChallenge, ZkpProof
from app.schemas.content import ChallengeRequest, ProofGenerateRequest, ProofVerifyRequest
from app.security.crypto import constant_time_compare, random_url_token, utcnow
from app.security.rate_limit import proof_limiter
from app.services.access import registration_or_404, require_registration_access, require_registration_owner, secret_for
from app.services.audit import append_audit
from app.services.notifications import notify
from app.zkp.sigma import SIGMA_SCHEME, generate_proof, public_signals, verify_proof

router = APIRouter(prefix="/zkp", tags=["zero-knowledge proofs"])

STATEMENT = (
    "The proof demonstrates knowledge of the opening of the registered ownership commitment "
    "without revealing the private secret. The selected file's SHA-256 fingerprint is compared "
    "locally and on the server before proving. The default sigma circuit does not verify the file "
    "hash inside the proof; that binding is explicit in the protocol and documented."
)


@router.post("/challenge")
def create_challenge(
    payload: ChallengeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    require_registration_owner(user, registration, db)
    previous = db.execute(
        select(ZkpChallenge).where(
            ZkpChallenge.registration_id == registration.id,
            ZkpChallenge.user_id == user.id,
            ZkpChallenge.purpose == payload.purpose,
            ZkpChallenge.used_at.is_(None),
        )
    ).scalars().all()
    for item in previous:
        item.used_at = utcnow()
    challenge = ZkpChallenge(
        registration_id=registration.id,
        user_id=user.id,
        nonce=random_url_token(32),
        purpose=payload.purpose,
        expires_at=utcnow() + timedelta(minutes=settings.zkp_challenge_minutes),
    )
    db.add(challenge)
    db.flush()
    append_audit(
        db,
        "zkp_challenge_created",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"challenge_id": challenge.id, "purpose": payload.purpose},
    )
    db.commit()
    return {
        "challenge_id": challenge.id,
        "nonce": challenge.nonce,
        "expires_at": challenge.expires_at.isoformat(),
        "registration_id": registration.registration_id,
        "registration_uuid": registration.id,
        "fingerprint": registration.sha256,
        "commitment": registration.commitment,
        "poseidon_commitment": registration.poseidon_commitment,
        "proof_system": SIGMA_SCHEME,
        "statement": STATEMENT,
        "is_groth16": False,
    }


@router.post("/generate")
def create_proof(
    payload: ProofGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed, retry_after = proof_limiter.check(f"proof:{user.id}", 40, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Proof generation rate limit exceeded. Retry in {retry_after} seconds.",
        )
    registration = registration_or_404(db, payload.registration_id)
    require_registration_owner(user, registration, db)
    if not constant_time_compare(registration.sha256, payload.file_sha256.lower()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected file fingerprint does not match the registered creation",
        )
    challenge = db.get(ZkpChallenge, payload.challenge_id)
    if not challenge or challenge.user_id != user.id or challenge.registration_id != registration.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    if challenge.used_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Challenge has already been used")
    if challenge.expires_at.tzinfo is None:
        challenge.expires_at = challenge.expires_at.replace(tzinfo=utcnow().tzinfo)
    if challenge.expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Challenge has expired. Request a new nonce.")
    secret_int, blinding_int = secret_for(registration)
    proof = generate_proof(
        registration.sha256,
        registration.registration_id,
        challenge.nonce,
        registration.commitment,
        secret_int,
        blinding_int,
    )
    challenge.used_at = utcnow()
    record = ZkpProof(
        registration_id=registration.id,
        user_id=user.id,
        challenge_id=challenge.id,
        scheme=proof["scheme"],
        public_signals=proof["public_signals"],
        proof=proof,
        status="generated",
    )
    db.add(record)
    db.flush()
    append_audit(
        db,
        "proof_generated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"proof_id": record.id, "scheme": proof["scheme"]},
    )
    notify(
        db,
        user.id,
        "proof",
        "Ownership proof generated",
        f"A zero-knowledge proof was generated for {registration.registration_id}.",
        "registration",
        registration.id,
    )
    db.commit()
    return {
        "proof_id": record.id,
        "proof": proof,
        "public_signals": proof["public_signals"],
        "scheme": proof["scheme"],
        "statement": STATEMENT,
        "expires_at": challenge.expires_at.isoformat(),
        "verification_url": None,
    }


@router.post("/verify")
def verify(
    payload: ProofVerifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    require_registration_access(user, registration, db)
    challenge = db.execute(
        select(ZkpChallenge).where(
            ZkpChallenge.nonce == payload.nonce,
            ZkpChallenge.registration_id == registration.id,
        )
    ).scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown challenge nonce")
    if challenge.expires_at.tzinfo is None:
        challenge.expires_at = challenge.expires_at.replace(tzinfo=utcnow().tzinfo)
    if challenge.expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Challenge has expired")
    existing = db.execute(
        select(ZkpProof).where(
            ZkpProof.registration_id == registration.id,
            ZkpProof.status == "verified",
            ZkpProof.challenge_id == challenge.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This proof has already been verified. Generate a fresh challenge.")
    valid, message = verify_proof(
        payload.proof,
        registration.sha256,
        registration.registration_id,
        payload.nonce,
        registration.commitment,
    )
    stated = payload.public_signals or payload.proof.get("public_signals") or {}
    if valid and (
        stated.get("registration_id") != registration.registration_id
        or stated.get("fingerprint") != registration.sha256
        or stated.get("challenge_nonce") != payload.nonce
    ):
        valid, message = False, "Public signals do not match the registered record"
    record = ZkpProof(
        registration_id=registration.id,
        user_id=user.id,
        challenge_id=challenge.id,
        scheme=payload.proof.get("scheme", SIGMA_SCHEME),
        public_signals=stated,
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
        ledger_service.record_proof_verification(db, user.id, record, registration)
        notify(
            db,
            registration.user_id,
            "proof",
            "Ownership proof verified",
            f"Proof verification succeeded for {registration.registration_id}.",
            "registration",
            registration.id,
        )
    append_audit(
        db,
        "proof_verified" if valid else "proof_verification_failed",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={"valid": valid, "message": message},
    )
    db.commit()
    return {
        "valid": valid,
        "message": message,
        "proof_system": payload.proof.get("scheme"),
        "registration_id": registration.registration_id,
        "verified_at": utcnow().isoformat() if valid else None,
        "statement": STATEMENT,
    }


@router.get("/proofs/{registration_id}")
def list_proofs(
    registration_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, registration_id)
    require_registration_access(user, registration, db)
    proofs = db.execute(
        select(ZkpProof).where(ZkpProof.registration_id == registration.id).order_by(ZkpProof.created_at.desc()).limit(50)
    ).scalars().all()
    return {
        "items": [
            {
                "id": proof.id,
                "scheme": proof.scheme,
                "status": proof.status,
                "public_signals": proof.public_signals,
                "created_at": proof.created_at.isoformat(),
                "verified_at": proof.verified_at.isoformat() if proof.verified_at else None,
            }
            for proof in proofs
        ],
        "statement": STATEMENT,
    }
