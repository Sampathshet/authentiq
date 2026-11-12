import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ledger import ledger_service
from app.models import (
    Commitment,
    FileMetadata,
    Registration,
    SimilarityAnalysis,
    TeamMember,
    TeamProject,
    TheftAlert,
    User,
)
from app.security.crypto import encrypt_text, utcnow
from app.services.analysis import dhash_bytes, extract_text
from app.services.audit import append_audit
from app.services.notifications import notify
from app.storage.files import iter_decrypted, read_decrypted
from app.zkp.sigma import create_commitment


def new_registration_id() -> str:
    year = datetime.now(timezone.utc).year
    return f"AQ-{year}-{secrets.token_hex(4).upper()}"


def read_limited(path: str, limit: int = 2_000_000) -> bytes:
    buffer = bytearray()
    for chunk in iter_decrypted(Path(path)):
        buffer.extend(chunk)
        if len(buffer) >= limit:
            return bytes(buffer[:limit])
    return bytes(buffer)


def inspect_file(registration_like, upload) -> tuple[str | None, str | None]:
    suffix = Path(upload.filename).suffix.lower()
    mime = upload.mime_type or ""
    perceptual = None
    text = None
    if mime.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        if upload.size_bytes <= 40 * 1024 * 1024:
            try:
                perceptual = dhash_bytes(read_decrypted(Path(upload.storage_path)))
            except Exception:
                perceptual = None
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        try:
            text = extract_text(read_limited(upload.storage_path), suffix)
        except Exception:
            text = None
    return perceptual, text


def resolve_team_project(db: Session, user: User, team_id: str | None) -> TeamProject | None:
    """Resolve the team project a creation is attributed to.

    Only the project owner and active members may attach a creation to a team.
    """
    if not team_id:
        return None
    project = db.get(TeamProject, team_id)
    if not project:
        project = db.execute(
            select(TeamProject).where(TeamProject.id == team_id)
        ).scalar_one_or_none()
    if not project:
        raise ValueError("Team project not found")
    if project.owner_id == user.id:
        return project
    membership = db.execute(
        select(TeamMember).where(
            TeamMember.project_id == project.id,
            TeamMember.user_id == user.id,
            TeamMember.status == "active",
        )
    ).scalar_one_or_none()
    if not membership:
        raise ValueError("You are not an active member of this team project")
    return project


def create_registration(
    db: Session,
    user: User,
    upload,
    title: str,
    description: str | None,
    asset_type: str,
    privacy: str,
    creation_timestamp: datetime | None,
    tags: list[str] | None,
    team_id: str | None = None,
    scope_to_organization: bool | None = None,
) -> tuple[Registration, FileMetadata, list[TheftAlert]]:
    existing_path = db.execute(
        select(Registration).where(Registration.storage_path == upload.storage_path)
    ).scalar_one_or_none()
    if existing_path:
        raise ValueError("This upload has already been registered")

    team_project = resolve_team_project(db, user, team_id)

    commitment = create_commitment(upload.final_sha256)
    registration_id = new_registration_id()
    while db.execute(select(Registration).where(Registration.registration_id == registration_id)).scalar_one_or_none():
        registration_id = new_registration_id()

    if creation_timestamp and creation_timestamp.tzinfo is None:
        creation_timestamp = creation_timestamp.replace(tzinfo=timezone.utc)
    if creation_timestamp and creation_timestamp > utcnow() + timedelta(days=1):
        raise ValueError("Creation timestamp cannot be in the future")

    organization_id = (
        user.organization_id
        if user.account_type == "organization"
        else (team_project.organization_id if team_project else None)
    )
    if scope_to_organization is True:
        organization_id = user.organization_id or (team_project.organization_id if team_project else None)
        if not organization_id:
            raise ValueError("You do not belong to an organization, so it cannot own this registration")
    elif scope_to_organization is False:
        organization_id = None

    registration = Registration(
        registration_id=registration_id,
        user_id=user.id,
        organization_id=organization_id,
        team_project_id=team_project.id if team_project else None,
        title=title,
        description=description,
        asset_type=asset_type,
        file_name=upload.filename,
        file_size=upload.size_bytes,
        mime_type=upload.mime_type,
        sha256=upload.final_sha256,
        commitment=commitment["pedersen_commitment"],
        poseidon_commitment=commitment["poseidon_commitment"],
        secret_encrypted=encrypt_text(format(commitment["secret_int"], "064x")),
        blinding_encrypted=encrypt_text(format(commitment["blinding_int"], "064x")),
        storage_path=upload.storage_path,
        privacy=privacy,
        status="registered",
        creation_timestamp=creation_timestamp,
        registered_at=utcnow(),
        tags=tags or [],
        is_demo=user.is_demo,
    )
    db.add(registration)
    db.flush()

    suffix = Path(upload.filename).suffix.lower()
    perceptual, text = inspect_file(registration, upload)
    metadata = FileMetadata(
        registration_id=registration.id,
        original_name=upload.filename,
        mime_type=upload.mime_type,
        extension=suffix,
        size_bytes=upload.size_bytes,
        encrypted_size_bytes=Path(upload.storage_path).stat().st_size if Path(upload.storage_path).exists() else 0,
        chunk_count=upload.total_chunks,
        perceptual_hash=perceptual,
        extracted_text=text,
        storage_path=upload.storage_path,
    )
    db.add(metadata)
    db.add(
        Commitment(
            registration_id=registration.id,
            scheme=commitment["scheme"],
            commitment_hex=commitment["pedersen_commitment"],
            poseidon_hex=commitment["poseidon_commitment"],
            fingerprint=upload.final_sha256,
        )
    )
    db.flush()

    ledger_tx = ledger_service.register_creation(db, user.id, registration)
    registration.ledger_tx_id = ledger_tx.tx_id

    alerts = detect_ownership_events(db, user, registration, metadata, upload.storage_path)

    append_audit(
        db,
        "creation_registered",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="registration",
        entity_id=registration.registration_id,
        metadata={
            "sha256": registration.sha256,
            "commitment": registration.commitment,
            "ledger_tx_id": registration.ledger_tx_id,
            "ledger_mode": registration.ledger_mode,
            "team_project_id": registration.team_project_id,
        },
    )
    notify(
        db,
        user.id,
        "registration",
        "Creation registered",
        f"{registration.title} was registered as {registration.registration_id}. Fingerprint {registration.sha256[:16]}...",
        "registration",
        registration.id,
    )
    if team_project:
        append_audit(
            db,
            "team_creation_registered",
            actor_id=user.id,
            actor_ref=user.email,
            entity_type="team_project",
            entity_id=team_project.id,
            metadata={"registration_id": registration.registration_id},
        )
        if team_project.owner_id != user.id:
            notify(
                db,
                team_project.owner_id,
                "team",
                "Team creation registered",
                f"{user.display_name} registered '{registration.title}' for {team_project.name}.",
                "team_project",
                team_project.id,
            )
    return registration, metadata, alerts


def duplicate_report(
    db: Session,
    user: User,
    sha256: str,
    perceptual_hash: str | None = None,
    exclude_registration_id: str | None = None,
) -> dict:
    from app.services.analysis import hamming_similarity

    candidates = db.execute(
        select(Registration, FileMetadata)
        .join(FileMetadata, FileMetadata.registration_id == Registration.id, isouter=True)
        .order_by(Registration.registered_at.desc())
        .limit(500)
    ).all()

    exact = []
    similar = []
    for candidate, candidate_meta in candidates:
        if exclude_registration_id and candidate.id == exclude_registration_id:
            continue
        if candidate.sha256 == sha256:
            exact.append(_match_payload(candidate, user, 1.0, "exact_sha256"))
            continue
        if perceptual_hash and candidate_meta and candidate_meta.perceptual_hash:
            score = hamming_similarity(perceptual_hash, candidate_meta.perceptual_hash)
            if score >= 0.90:
                similar.append(_match_payload(candidate, user, score, "perceptual_hash"))
    similar.sort(key=lambda item: item["similarity"], reverse=True)
    return {
        "exact_matches": exact,
        "similar_matches": similar[:25],
        "checked": True,
        "explanation": "Exact matches share an identical SHA-256 fingerprint. Similar matches use a dHash-64 perceptual comparison of the image.",
    }


def _match_payload(candidate: Registration, user: User, score: float, method: str) -> dict:
    return {
        "registration_id": candidate.registration_id,
        "id": candidate.id,
        "title": candidate.title,
        "file_name": candidate.file_name,
        "asset_type": candidate.asset_type,
        "registered_at": candidate.registered_at.isoformat() if candidate.registered_at else None,
        "similarity": score,
        "method": method,
        "owned_by_you": candidate.user_id == user.id,
        "same_organization": bool(
            user.organization_id and candidate.organization_id == user.organization_id
        ),
    }


def detect_ownership_events(db: Session, user: User, registration: Registration, metadata: FileMetadata, storage_path: str) -> list[TheftAlert]:
    candidates = db.execute(
        select(Registration, FileMetadata)
        .join(FileMetadata, FileMetadata.registration_id == Registration.id, isouter=True)
        .where(Registration.id != registration.id)
        .order_by(Registration.registered_at.desc())
        .limit(500)
    ).all()
    created_alerts = []
    exact_matches = [(candidate, candidate_meta) for candidate, candidate_meta in candidates if candidate.sha256 == registration.sha256]

    for candidate, candidate_meta in exact_matches:
        if candidate.user_id == user.id:
            continue
        existing = db.execute(
            select(TheftAlert).where(
                TheftAlert.registration_id == registration.id,
                TheftAlert.matched_registration_id == candidate.id,
                TheftAlert.alert_type == "exact_duplicate",
            )
        ).scalar_one_or_none()
        if existing:
            continue
        for owner_id, entity_id in [(candidate.user_id, candidate.id), (user.id, registration.id)]:
            alert = TheftAlert(
                owner_id=owner_id,
                registration_id=registration.id,
                matched_registration_id=candidate.id,
                alert_type="exact_duplicate",
                similarity_score=1.0,
                status="new",
                notification_sent=True,
            )
            db.add(alert)
            created_alerts.append(alert)
            notify(
                db,
                owner_id,
                "duplicate_fingerprint",
                "Exact fingerprint match detected",
                f"Registration {registration.registration_id} shares an identical SHA-256 fingerprint with {candidate.registration_id}.",
                "registration",
                entity_id,
            )
        append_audit(
            db,
            "duplicate_fingerprint_detected",
            actor_id=user.id,
            actor_ref=user.email,
            entity_type="registration",
            entity_id=registration.registration_id,
            metadata={"matched_registration_id": candidate.registration_id, "sha256": registration.sha256},
        )

    from app.services.analysis import analyze_duplicates

    results = analyze_duplicates(
        registration,
        metadata,
        [(candidate, candidate_meta) for candidate, candidate_meta in candidates if candidate_meta is not None],
    )
    for result in results:
        if result["method"] == "exact_sha256":
            continue
        record = SimilarityAnalysis(
            registration_id=registration.id,
            compared_registration_id=result["registration"].id,
            method=result["method"],
            score=result["score"],
            details=result["details"],
        )
        db.add(record)
        if result["score"] >= 0.9:
            existing = db.execute(
                select(TheftAlert).where(
                    TheftAlert.registration_id == registration.id,
                    TheftAlert.matched_registration_id == result["registration"].id,
                    TheftAlert.alert_type == "modified_content",
                )
            ).scalar_one_or_none()
            if not existing:
                alert = TheftAlert(
                    owner_id=result["registration"].user_id,
                    registration_id=registration.id,
                    matched_registration_id=result["registration"].id,
                    alert_type="modified_content",
                    similarity_score=result["score"],
                    status="new",
                    notification_sent=True,
                )
                db.add(alert)
                created_alerts.append(alert)
                notify(
                    db,
                    result["registration"].user_id,
                    "suspicious_claim",
                    "Similar content registered",
                    f"An investigation indicator with {result['method']} similarity {result['score']:.2f} was created. This is not a finding of infringement.",
                    "registration",
                    registration.id,
                )
    db.flush()
    return created_alerts
