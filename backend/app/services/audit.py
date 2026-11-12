import hashlib
import json
import threading
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import AuditLog

GENESIS_AUDIT_HASH = "0" * 64

_audit_lock = threading.RLock()
_AUDIT_ADVISORY_LOCK_KEY = 728411903


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _audit_timestamp(value) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat()


def _lock_audit_chain(db: Session) -> None:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _AUDIT_ADVISORY_LOCK_KEY})


def append_audit(
    db: Session,
    action: str,
    actor_id: str | None = None,
    actor_ref: str = "system",
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    with _audit_lock:
        _lock_audit_chain(db)
        last = db.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(1)
        ).scalar_one_or_none()
        prev_hash = last.record_hash if last else GENESIS_AUDIT_HASH
        created_at = datetime.now(timezone.utc)
        event_id = f"evt_{uuid4().hex}"
        body = {
            "event_id": event_id,
            "actor_id": actor_id,
            "actor_ref": actor_ref,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata or {},
            "created_at": _audit_timestamp(created_at),
        }
        record_hash = hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()
        entry = AuditLog(
            event_id=event_id,
            actor_id=actor_id,
            actor_ref=actor_ref,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=metadata or {},
            ip_address=ip_address,
            user_agent=(user_agent or "")[:400] or None,
            prev_hash=prev_hash,
            record_hash=record_hash,
            created_at=created_at,
        )
        db.add(entry)
        db.flush()
        return entry


def verify_audit_chain(db: Session) -> dict:
    entries = db.execute(select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())).scalars().all()
    previous = GENESIS_AUDIT_HASH
    errors = []
    for entry in entries:
        body = {
            "event_id": entry.event_id,
            "actor_id": entry.actor_id,
            "actor_ref": entry.actor_ref,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "metadata": entry.event_metadata or {},
            "created_at": _audit_timestamp(entry.created_at),
        }
        expected = hashlib.sha256((previous + _canonical(body)).encode("utf-8")).hexdigest()
        if entry.prev_hash != previous:
            errors.append(f"Audit chain link mismatch at {entry.event_id}")
        if entry.record_hash != expected:
            errors.append(f"Audit record hash mismatch at {entry.event_id}")
        previous = entry.record_hash
    return {"valid": len(errors) == 0, "events": len(entries), "errors": errors, "last_hash": previous}
