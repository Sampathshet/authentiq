import threading

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import AuditLog
from app.services.audit import append_audit, verify_audit_chain


def test_parallel_audit_appends_keep_the_chain_valid(client):
    errors = []

    def worker(index):
        db = SessionLocal()
        try:
            append_audit(db, "concurrency_probe", actor_ref=f"probe-{index}", entity_type="probe", entity_id=str(index))
            db.commit()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, errors
    db = SessionLocal()
    try:
        result = verify_audit_chain(db)
    finally:
        db.close()
    assert result["valid"], result["errors"]
    assert result["events"] >= 12


def test_audit_chain_detects_tampering(client):
    db = SessionLocal()
    try:
        append_audit(db, "tamper_probe", actor_ref="probe", entity_type="probe", entity_id="1")
        db.commit()
        entry = db.execute(select(AuditLog).order_by(AuditLog.created_at.asc()).limit(1)).scalar_one()
        event_id = entry.event_id
        original = entry.record_hash
        entry.record_hash = "0" * 64
        db.commit()
        result = verify_audit_chain(db)
    finally:
        db.close()
    assert not result["valid"]
    assert any("hash mismatch" in error for error in result["errors"])

    db = SessionLocal()
    try:
        row = db.execute(select(AuditLog).where(AuditLog.event_id == event_id)).scalar_one()
        row.record_hash = original
        db.commit()
        repaired = verify_audit_chain(db)
    finally:
        db.close()
    assert repaired["valid"], repaired["errors"]
