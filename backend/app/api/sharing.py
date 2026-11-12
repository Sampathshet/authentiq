from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user
from app.ledger import ledger_service
from app.models import Idea, Registration, TeamProject, User, VerificationRequest, ZkpChallenge, ZkpProof
from app.schemas.content import PublicVerifyRequest, ShareCreateRequest
from app.security.crypto import random_url_token, utcnow
from app.security.rate_limit import proof_limiter
from app.services.access import registration_or_404, require_registration_owner, secret_for
from app.services.audit import append_audit
from app.services.certificate import verification_url_for
from app.services.notifications import notify
from app.zkp.sigma import SIGMA_SCHEME, generate_proof, verify_proof

router = APIRouter(prefix="/sharing", tags=["silent sharing"])
public_router = APIRouter(prefix="/public", tags=["public verification"])

DEFAULT_DISCLOSURE = {
    "show_reference": True,
    "show_registration_date": True,
    "show_fingerprint": False,
    "show_organization": False,
    "anonymous": True,
}


def _clean_disclosure(raw: dict) -> dict:
    disclosure = dict(DEFAULT_DISCLOSURE)
    for key in DEFAULT_DISCLOSURE:
        if key in raw:
            disclosure[key] = bool(raw[key])
    return disclosure


def _team_name(db: Session, registration) -> str | None:
    """Name of the team project a registration belongs to, if any."""
    if not getattr(registration, "team_project_id", None):
        return None
    project = db.get(TeamProject, registration.team_project_id)
    return project.name if project else None


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_share(
    payload: ShareCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    registration = registration_or_404(db, payload.registration_id)
    require_registration_owner(user, registration, db)
    allowed, retry_after = proof_limiter.check(f"share:{user.id}", 30, 3600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Verification link rate limit exceeded. Retry in {retry_after} seconds.",
        )
    disclosure = _clean_disclosure(payload.disclosure)
    expires_at = utcnow() + timedelta(hours=payload.expires_in_hours)
    challenge = ZkpChallenge(
        registration_id=registration.id,
        user_id=user.id,
        nonce=random_url_token(32),
        purpose="share",
        expires_at=expires_at,
        used_at=utcnow(),
    )
    db.add(challenge)
    db.flush()
    secret_int, blinding_int = secret_for(registration)
    proof = generate_proof(
        registration.sha256,
        registration.registration_id,
        challenge.nonce,
        registration.commitment,
        secret_int,
        blinding_int,
    )
    proof_record = ZkpProof(
        registration_id=registration.id,
        user_id=user.id,
        challenge_id=challenge.id,
        scheme=proof["scheme"],
        public_signals=proof["public_signals"],
        proof=proof,
        status="generated",
    )
    db.add(proof_record)
    db.flush()
    verification = VerificationRequest(
        verification_id="vrf_" + random_url_token(24),
        registration_id=registration.id,
        creator_id=user.id,
        challenge_id=challenge.id,
        nonce=challenge.nonce,
        disclosure=disclosure,
        message=payload.message,
        expires_at=expires_at,
        max_uses=payload.max_uses,
        status="pending",
        proof_id=proof_record.id,
    )
    db.add(verification)
    db.flush()
    append_audit(
        db,
        "silent_sharing_created",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="verification_request",
        entity_id=verification.verification_id,
        metadata={"registration_id": registration.registration_id, "expires_at": expires_at.isoformat()},
    )
    notify(
        db,
        user.id,
        "verification",
        "Silent sharing link created",
        f"A privacy-preserving verification link was created for {registration.registration_id}.",
        "verification_request",
        verification.id,
    )
    db.commit()
    package = {
        "format": "AUTHENTIQ-VERIFICATION-PACKAGE-V1",
        "verification_id": verification.verification_id,
        "registration_reference": registration.registration_id,
        "nonce": verification.nonce,
        "proof": proof,
        "public_signals": proof["public_signals"],
        "disclosure": disclosure,
        "issued_at": utcnow().isoformat(),
    }
    return {
        "verification_id": verification.verification_id,
        "verification_url": verification_url_for(verification.verification_id),
        "expires_at": verification.expires_at.isoformat(),
        "max_uses": verification.max_uses,
        "disclosure": disclosure,
        "proof_system": SIGMA_SCHEME,
        "proof_package": package,
    }


@router.get("")
def list_shares(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(
        select(VerificationRequest, Registration)
        .join(Registration, VerificationRequest.registration_id == Registration.id)
        .where(VerificationRequest.creator_id == user.id)
        .order_by(VerificationRequest.created_at.desc())
        .limit(100)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "verification_id": item.verification_id,
                "verification_url": verification_url_for(item.verification_id),
                "registration_id": item.registration_id,
                "registration_label": registration.registration_id,
                "registration_title": registration.title,
                "status": item.status,
                "result": item.result,
                "uses": item.uses,
                "max_uses": item.max_uses,
                "disclosure": item.disclosure,
                "message": item.message,
                "created_at": item.created_at.isoformat(),
                "expires_at": item.expires_at.isoformat(),
                "verified_at": item.verified_at.isoformat() if item.verified_at else None,
                "expired": item.expires_at.replace(tzinfo=utcnow().tzinfo) < utcnow() if item.expires_at.tzinfo is None else item.expires_at < utcnow(),
            }
            for item, registration in items
        ]
    }


@router.delete("/{verification_id}")
def revoke_share(verification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    verification = db.execute(
        select(VerificationRequest).where(VerificationRequest.verification_id == verification_id)
    ).scalar_one_or_none()
    if not verification or verification.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")
    verification.status = "revoked"
    append_audit(
        db,
        "silent_sharing_revoked",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="verification_request",
        entity_id=verification.verification_id,
    )
    db.commit()
    return {"message": "Verification request revoked"}


@public_router.get("/verify/{verification_id}")
def public_verification(verification_id: str, db: Session = Depends(get_db)):
    verification = db.execute(
        select(VerificationRequest).where(VerificationRequest.verification_id == verification_id)
    ).scalar_one_or_none()
    if verification:
        registration = db.get(Registration, verification.registration_id)
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
        now = utcnow()
        expiry = verification.expires_at if verification.expires_at.tzinfo else verification.expires_at.replace(tzinfo=now.tzinfo)
        expired = expiry < now
        disclosure = verification.disclosure or DEFAULT_DISCLOSURE
        return {
            "kind": "verification_request",
            "verification_id": verification.verification_id,
            "status": "expired" if expired else verification.status,
            "result": verification.result,
            "message": verification.message,
            "expires_at": verification.expires_at.isoformat(),
            "verified_at": verification.verified_at.isoformat() if verification.verified_at else None,
            "uses": verification.uses,
            "max_uses": verification.max_uses,
            "requires_proof": verification.status in {"pending", "failed"} and not expired,
            "disclosure": disclosure,
            "public_record": {
                "registration_reference": registration.registration_id if disclosure.get("show_reference", True) else None,
                "title": registration.title if registration.privacy == "public" else None,
                "fingerprint": registration.sha256 if disclosure.get("show_fingerprint") else None,
                "registered_at": registration.registered_at.isoformat() if disclosure.get("show_registration_date", True) else None,
                "commitment": registration.commitment if registration.privacy != "private" else None,
                "ledger_mode": registration.ledger_mode,
                "ledger_tx_id": registration.ledger_tx_id,
                "organization": "Organization member" if disclosure.get("show_organization") and registration.organization_id else None,
                "team": _team_name(db, registration),
            },
            "proof_system": SIGMA_SCHEME,
            "privacy_note": "No original file, private witness, password, or personal identity is exposed by this endpoint.",
        }
    registration = db.execute(
        select(Registration).where(Registration.registration_id == verification_id)
    ).scalar_one_or_none()
    if registration:
        if registration.privacy == "private":
            return {
                "kind": "registration",
                "verification_id": verification_id,
                "status": "private",
                "requires_proof": False,
                "available": False,
                "message": "This registration is private. Request a silent-sharing verification link from the owner.",
                "public_record": {
                    "registration_reference": registration.registration_id,
                    "ledger_mode": registration.ledger_mode,
                    "registered_at": None,
                    "fingerprint": None,
                    "commitment": None,
                },
            }
        return {
            "kind": "registration",
            "verification_id": verification_id,
            "status": "registered",
            "requires_proof": False,
            "available": True,
            "public_record": {
                "registration_reference": registration.registration_id,
                "title": registration.title if registration.privacy == "public" else None,
                "fingerprint": registration.sha256,
                "commitment": registration.commitment,
                "registered_at": registration.registered_at.isoformat(),
                "ledger_mode": registration.ledger_mode,
                "ledger_tx_id": registration.ledger_tx_id,
                "organization": None,
                "team": _team_name(db, registration),
            },
            "message": "Public registration metadata is available. Submit an ownership proof for cryptographic verification.",
        }
    idea = db.execute(select(Idea).where(Idea.idea_ref == verification_id)).scalar_one_or_none()
    if idea:
        return {
            "kind": "idea",
            "verification_id": verification_id,
            "status": "protected" if idea.status != "revealed" else "revealed",
            "requires_proof": False,
            "available": True,
            "public_record": {
                "registration_reference": idea.idea_ref,
                "title": idea.title if idea.status == "revealed" else None,
                "fingerprint": None,
                "commitment": idea.commitment,
                "registered_at": idea.created_at.isoformat(),
                "ledger_mode": idea.ledger_mode,
                "ledger_tx_id": idea.ledger_tx_id,
                "organization": None,
            },
            "message": "This idea commitment is timestamped. The private idea description is not public.",
        }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")


@public_router.post("/verify/{verification_id}")
def verify_public_proof(
    verification_id: str,
    payload: PublicVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = client_ip(request)
    allowed, retry_after = proof_limiter.check(f"public-verify:{ip}", 30, 600)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many verification attempts. Retry in {retry_after} seconds.",
        )
    verification = db.execute(
        select(VerificationRequest).where(VerificationRequest.verification_id == verification_id)
    ).scalar_one_or_none()
    if not verification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found")
    now = utcnow()
    expiry = verification.expires_at if verification.expires_at.tzinfo else verification.expires_at.replace(tzinfo=now.tzinfo)
    if verification.status == "revoked":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Verification request has been revoked")
    if expiry < now:
        verification.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Verification request has expired")
    if verification.uses >= verification.max_uses:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Verification request has reached its usage limit")
    registration = db.get(Registration, verification.registration_id)
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    package = payload.proof_package or {}
    proof = payload.proof or package.get("proof")
    signals = payload.public_signals or package.get("public_signals") or (proof or {}).get("public_signals") or {}
    nonce = package.get("nonce") or signals.get("challenge_nonce") or verification.nonce
    if not proof:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A proof package is required")
    if signals.get("registration_id") != registration.registration_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Proof registration reference does not match this request")
    if signals.get("fingerprint") != registration.sha256:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Proof fingerprint does not match the registered record")
    if nonce != verification.nonce:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Proof nonce does not match this one-time challenge")

    valid, message = verify_proof(
        proof,
        registration.sha256,
        registration.registration_id,
        verification.nonce,
        registration.commitment,
    )
    verification.uses += 1
    verification.result = "valid" if valid else "invalid"
    verification.status = "verified" if valid else "failed"
    verification.verified_at = now if valid else None
    if valid:
        registration.verified_at = now
        if registration.status == "registered":
            registration.status = "verified"
        stored_proof = ZkpProof(
            registration_id=registration.id,
            user_id=verification.creator_id,
            challenge_id=verification.challenge_id,
            scheme=proof.get("scheme", SIGMA_SCHEME),
            public_signals=signals,
            proof=proof,
            status="verified",
            verified_at=now,
        )
        db.add(stored_proof)
        db.flush()
        ledger_service.record_proof_verification(db, verification.creator_id, stored_proof, registration)
        notify(
            db,
            verification.creator_id,
            "verification",
            "Silent share verified",
            f"A verifier validated the ownership proof for {registration.registration_id}.",
            "verification_request",
            verification.id,
        )
    append_audit(
        db,
        "silent_share_verification",
        actor_ref=f"public:{ip}",
        entity_type="verification_request",
        entity_id=verification.verification_id,
        metadata={"valid": valid, "message": message, "ip": ip},
    )
    db.commit()
    disclosure = verification.disclosure or DEFAULT_DISCLOSURE
    return {
        "valid": valid,
        "result": verification.result,
        "message": message,
        "verification_id": verification.verification_id,
        "verified_at": now.isoformat() if valid else None,
        "registration_reference": registration.registration_id if disclosure.get("show_reference", True) else None,
        "fingerprint": registration.sha256 if disclosure.get("show_fingerprint") else None,
        "registered_at": registration.registered_at.isoformat() if disclosure.get("show_registration_date", True) else None,
        "ledger_mode": registration.ledger_mode,
        "ledger_tx_id": registration.ledger_tx_id,
        "uses": verification.uses,
        "max_uses": verification.max_uses,
        "statement": "The proof proves knowledge of the commitment opening. File fingerprint equality is checked separately and is not inside the default sigma circuit.",
    }
