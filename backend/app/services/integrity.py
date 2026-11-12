import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ledger import ledger_service
from app.models import (
    Dispute,
    FileMetadata,
    Idea,
    Notification,
    Registration,
    TeamProject,
    TheftAlert,
    ZkpProof,
)
from app.services.certificate import build_registration_certificate, verification_url_for
from app.storage.files import iter_decrypted


def _iso(value) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str | None:
    if not path.exists():
        return None
    hasher = hashlib.sha256()
    try:
        for chunk in iter_decrypted(path):
            hasher.update(chunk)
    except Exception:
        return None
    return hasher.hexdigest()


def trust_report(db: Session, registration: Registration, metadata: FileMetadata | None, verify_file: bool = True) -> dict:
    factors = []
    score = 0

    fingerprint_points = 20 if registration.sha256 else 0
    if registration.sha256 and registration.poseidon_commitment:
        fingerprint_points = 25
    factors.append(
        {
            "key": "fingerprint",
            "label": "Cryptographic fingerprint",
            "points": fingerprint_points,
            "max": 25,
            "detail": "SHA-256 fingerprint with a Poseidon commitment bound to an encrypted secret."
            if fingerprint_points == 25
            else "Fingerprint is incomplete.",
        }
    )
    score += fingerprint_points

    ledger_record = ledger_service.verify_record(registration.ledger_tx_id) if registration.ledger_tx_id else None
    if ledger_record and ledger_record.get("record_hash"):
        ledger_points = 25
        ledger_detail = f"Confirmed in the {ledger_record.get('network', 'AUTHENTIQ')} at block {ledger_record.get('block_number')}."
    elif registration.ledger_tx_id:
        ledger_points = 10
        ledger_detail = "A transaction reference exists but the ledger record could not be re-read."
    else:
        ledger_points = 0
        ledger_detail = "No ledger record is attached to this registration."
    factors.append(
        {
            "key": "ledger",
            "label": "Ledger confirmation",
            "points": ledger_points,
            "max": 25,
            "detail": ledger_detail,
        }
    )
    score += ledger_points

    verified_proofs = db.execute(
        select(func.count())
        .select_from(ZkpProof)
        .where(ZkpProof.registration_id == registration.id, ZkpProof.status == "verified")
    ).scalar_one()
    any_proofs = db.execute(
        select(func.count()).select_from(ZkpProof).where(ZkpProof.registration_id == registration.id)
    ).scalar_one()
    proof_points = min(20, int(verified_proofs) * 10)
    factors.append(
        {
            "key": "proofs",
            "label": "Zero-knowledge proofs",
            "points": proof_points,
            "max": 20,
            "detail": (
                f"{verified_proofs} verified proof(s) out of {any_proofs} generated."
                if any_proofs
                else "No ownership proof has been generated yet."
            ),
        }
    )
    score += proof_points

    if verify_file:
        digest = file_digest(Path(registration.storage_path))
        if digest is None:
            integrity_points = 0
            integrity_detail = "The stored encrypted file is missing or unreadable."
        elif digest == registration.sha256:
            integrity_points = 15
            integrity_detail = "The decrypted file still hashes to the registered fingerprint."
        else:
            integrity_points = 0
            integrity_detail = "The decrypted file no longer matches the registered fingerprint."
    else:
        integrity_points = 0
        integrity_detail = "File integrity check was skipped for this request."
    factors.append(
        {
            "key": "file_integrity",
            "label": "Stored file integrity",
            "points": integrity_points,
            "max": 15,
            "detail": integrity_detail,
        }
    )
    score += integrity_points

    if metadata and metadata.perceptual_hash:
        factors.append(
            {
                "key": "visual_signature",
                "label": "Perceptual signature",
                "points": 5,
                "max": 5,
                "detail": "A dHash-64 perceptual signature lets the workspace match re-encoded copies of this image.",
            }
        )
        score += 5
    else:
        factors.append(
            {
                "key": "visual_signature",
                "label": "Perceptual signature",
                "points": 0,
                "max": 5,
                "detail": "No perceptual signature applies to this file type.",
            }
        )

    duplicate_count = db.execute(
        select(func.count())
        .select_from(TheftAlert)
        .where(
            (TheftAlert.registration_id == registration.id)
            | (TheftAlert.matched_registration_id == registration.id)
        )
    ).scalar_one()
    duplicate_penalty = min(15, int(duplicate_count) * 5)
    factors.append(
        {
            "key": "duplicates",
            "label": "Duplicate indicators",
            "points": -duplicate_penalty,
            "max": 0,
            "detail": (
                f"{duplicate_count} duplicate or similarity indicator(s) involve this record."
                if duplicate_count
                else "No duplicate or similarity indicator involves this record."
            ),
        }
    )
    score -= duplicate_penalty

    open_disputes = db.execute(
        select(func.count())
        .select_from(Dispute)
        .where(
            (Dispute.registration_id == registration.id),
            Dispute.status.in_(["open", "under_review", "escalated"]),
        )
    ).scalar_one()
    dispute_penalty = min(20, int(open_disputes) * 10)
    factors.append(
        {
            "key": "disputes",
            "label": "Open disputes",
            "points": -dispute_penalty,
            "max": 0,
            "detail": (
                f"{open_disputes} open dispute(s) reference this record."
                if open_disputes
                else "No open dispute references this record."
            ),
        }
    )
    score -= dispute_penalty

    score = max(0, min(100, score))
    if score >= 90:
        grade = "verified"
        summary = "Strong, corroborated ownership evidence."
    elif score >= 70:
        grade = "strong"
        summary = "Solid evidence with minor gaps."
    elif score >= 45:
        grade = "developing"
        summary = "Partial evidence. Generate a proof to strengthen it."
    else:
        grade = "unverified"
        summary = "Insufficient evidence. Register, anchor, and prove ownership."
    return {
        "score": score,
        "grade": grade,
        "summary": summary,
        "factors": factors,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def evidence_manifest(
    db: Session,
    registration: Registration,
    metadata: FileMetadata | None,
    owner_name: str,
    proofs: list[ZkpProof],
    trust: dict,
) -> dict:
    ledger_record = ledger_service.verify_record(registration.ledger_tx_id) if registration.ledger_tx_id else None
    body = {
        "schema": "authentiq-evidence-packet/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registration": {
            "registration_id": registration.registration_id,
            "title": registration.title,
            "description": registration.description,
            "asset_type": registration.asset_type,
            "privacy": registration.privacy,
            "status": registration.status,
            "owner": owner_name,
            "registered_at": _iso(registration.registered_at),
            "creation_timestamp": _iso(registration.creation_timestamp),
            "file_name": registration.file_name,
            "file_size": registration.file_size,
            "mime_type": registration.mime_type,
            "sha256": registration.sha256,
            "commitment": registration.commitment,
            "poseidon_commitment": registration.poseidon_commitment,
            "tags": registration.tags or [],
        },
        "file_metadata": {
            "extension": metadata.extension if metadata else None,
            "chunk_count": metadata.chunk_count if metadata else None,
            "encrypted_size_bytes": metadata.encrypted_size_bytes if metadata else None,
            "perceptual_hash": metadata.perceptual_hash if metadata else None,
        },
        "ledger": {
            "mode": registration.ledger_mode,
            "tx_id": registration.ledger_tx_id,
            "simulated": registration.ledger_mode == "simulation",
            "record": ledger_record,
        },
        "proofs": [
            {
                "id": proof.id,
                "scheme": proof.scheme,
                "status": proof.status,
                "public_signals": proof.public_signals,
                "created_at": _iso(proof.created_at),
                "verified_at": _iso(proof.verified_at),
            }
            for proof in proofs
        ],
        "trust": {
            "score": trust["score"],
            "grade": trust["grade"],
            "factors": trust["factors"],
        },
        "verification_url": verification_url_for(registration.registration_id),
        "artifacts": ["certificate.pdf", "ledger-receipt.json", "file.sha256.txt", "VERIFY.txt"],
    }
    body["manifest_sha256"] = _digest(body)
    return body


def build_evidence_packet(
    db: Session,
    registration: Registration,
    metadata: FileMetadata | None,
    owner_name: str,
    proofs: list[ZkpProof],
) -> bytes:
    trust = trust_report(db, registration, metadata)
    manifest = evidence_manifest(db, registration, metadata, owner_name, proofs, trust)
    certificate = build_registration_certificate(
        registration, owner_name, verification_url_for(registration.registration_id)
    )
    ledger_record = ledger_service.verify_record(registration.ledger_tx_id) if registration.ledger_tx_id else None
    receipt = {
        "registration_id": registration.registration_id,
        "tx_id": registration.ledger_tx_id,
        "mode": registration.ledger_mode,
        "simulated": registration.ledger_mode == "simulation",
        "network": ledger_record.get("network") if ledger_record else None,
        "block_number": ledger_record.get("block_number") if ledger_record else None,
        "record_hash": ledger_record.get("record_hash") if ledger_record else None,
        "prev_hash": ledger_record.get("prev_hash") if ledger_record else None,
        "payload_digest": ledger_record.get("payload_digest") if ledger_record else None,
        "record": ledger_record,
    }
    instructions = "\n".join(
        [
            "AUTHENTIQ EVIDENCE PACKET",
            "",
            f"Registration: {registration.registration_id}",
            f"File: {registration.file_name}",
            f"SHA-256: {registration.sha256}",
            f"Poseidon commitment: {registration.poseidon_commitment}",
            f"Verification URL: {verification_url_for(registration.registration_id)}",
            "",
            "How to verify this packet",
            "1. Hash the original file with SHA-256 and compare it to the value above.",
            "2. Open certificate.pdf and confirm the registration ID and fingerprint match.",
            "3. Compare ledger-receipt.json with the ledger block reported by the AUTHENTIQ API.",
            "4. Open the verification URL and complete the public verification flow.",
            "5. Recompute the SHA-256 of manifest.json and compare it with manifest_sha256 inside it.",
            "",
            "The default zero-knowledge proof proves knowledge of the commitment opening.",
            "File-hash equality and the Poseidon relation are checked by the API outside the proof circuit.",
            "",
            "Ledger mode: "
            + registration.ledger_mode
            + (" (local append-only simulation, not a public blockchain transaction)"
               if registration.ledger_mode == "simulation"
               else ""),
        ]
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        archive.writestr("certificate.pdf", certificate)
        archive.writestr("ledger-receipt.json", json.dumps(receipt, indent=2, sort_keys=True))
        archive.writestr("file.sha256.txt", f"{registration.sha256}  {registration.file_name}\n")
        archive.writestr("VERIFY.txt", instructions)
    return buffer.getvalue()


def workspace_overview(db: Session, user: Registration) -> dict:
    ledger_audit = ledger_service.audit()
    status = ledger_service.status()
    registrations = db.execute(select(Registration).where(Registration.user_id == user.id)).scalars().all()
    metadata_rows = db.execute(
        select(FileMetadata).where(FileMetadata.registration_id.in_([item.id for item in registrations]))
    ).scalars().all() if registrations else []
    metadata_map = {item.registration_id: item for item in metadata_rows}
    missing_ledger = [item.registration_id for item in registrations if item.ledger_tx_id and not ledger_service.verify_record(item.ledger_tx_id)]
    missing_files = [item.registration_id for item in registrations if not Path(item.storage_path).exists()]
    duplicate_groups = db.execute(
        select(Registration.sha256, func.count(Registration.id))
        .where(Registration.user_id == user.id)
        .group_by(Registration.sha256)
        .having(func.count(Registration.id) > 1)
    ).all()
    counts = {
        "registrations": len(registrations),
        "ideas": db.execute(select(func.count()).select_from(Idea).where(Idea.user_id == user.id)).scalar_one(),
        "teams": db.execute(select(func.count()).select_from(TeamProject).where(TeamProject.owner_id == user.id)).scalar_one(),
        "alerts": db.execute(select(func.count()).select_from(TheftAlert).where(TheftAlert.owner_id == user.id)).scalar_one(),
        "notifications": db.execute(select(func.count()).select_from(Notification).where(Notification.user_id == user.id)).scalar_one(),
        "proofs": db.execute(
            select(func.count()).select_from(ZkpProof).where(ZkpProof.registration_id.in_([item.id for item in registrations]))
        ).scalar_one() if registrations else 0,
    }
    snapshot = [
        {
            "registration_id": item.registration_id,
            "sha256": item.sha256,
            "ledger_tx_id": item.ledger_tx_id,
            "registered_at": _iso(item.registered_at),
            "perceptual_hash": metadata_map.get(item.id).perceptual_hash if metadata_map.get(item.id) else None,
        }
        for item in sorted(registrations, key=lambda entry: entry.registered_at)
    ]
    return {
        "ledger": {
            "valid": ledger_audit.get("valid"),
            "records": ledger_audit.get("records"),
            "last_hash": ledger_audit.get("last_hash"),
            "errors": ledger_audit.get("errors", []),
            "mode": status.get("mode"),
            "label": status.get("label"),
            "network": status.get("network"),
            "tamper_detected": status.get("tamper_detected"),
        },
        "counts": counts,
        "checks": {
            "missing_ledger_records": missing_ledger,
            "missing_files": missing_files,
            "duplicate_fingerprints": [{"sha256": row[0], "count": row[1]} for row in duplicate_groups],
        },
        "workspace_digest": _digest(snapshot),
        "records": [
            {
                "registration_id": item.registration_id,
                "title": item.title,
                "asset_type": item.asset_type,
                "sha256": item.sha256,
                "ledger_tx_id": item.ledger_tx_id,
                "ledger_ok": bool(item.ledger_tx_id and ledger_service.verify_record(item.ledger_tx_id)),
                "file_present": Path(item.storage_path).exists(),
                "registered_at": _iso(item.registered_at),
            }
            for item in registrations
        ],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
