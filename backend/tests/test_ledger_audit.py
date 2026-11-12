import json

from app.core.database import SessionLocal
from app.core.config import settings
from app.models import AuditLog
from tests.helpers import create_registration, register_user


def _ledger_records():
    return [json.loads(line) for line in settings.ledger_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_append_only_ledger_records_and_audit(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"])
    registration = created["registration"]

    status = client.get("/api/ledger/status", headers=user["headers"])
    assert status.status_code == 200
    body = status.json()
    assert body["mode"] == "simulation"
    assert body["label"] == "Simulation Mode"
    assert body["tamper_detected"] is False
    assert body["database_records"] >= 1
    assert "No public blockchain transaction" in body["message"]

    transactions = client.get("/api/ledger/transactions", headers=user["headers"])
    assert transactions.status_code == 200
    items = transactions.json()["items"]
    assert transactions.json()["simulated"] is True
    assert any(item["tx_type"] == "creation_registered" for item in items)

    tx_id = registration["ledger_tx_id"]
    detail = client.get(f"/api/ledger/transactions/{tx_id}", headers=user["headers"])
    assert detail.status_code == 200
    assert detail.json()["integrity"]["matches"] is True

    audit = client.post("/api/ledger/audit", headers=user["headers"])
    assert audit.status_code == 200
    assert audit.json()["valid"] is True
    assert audit.json()["records"] >= 1


def test_ledger_tampering_is_detected(client, user_factory):
    user = user_factory()
    create_registration(client, user["headers"])

    records = _ledger_records()
    assert records
    records[0]["payload"]["fingerprint"] = "f" * 64
    settings.ledger_file.write_text(
        "\n".join(json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records) + "\n",
        encoding="utf-8",
    )

    audit = client.post("/api/ledger/audit", headers=user["headers"])
    assert audit.status_code == 200
    report = audit.json()
    assert report["valid"] is False
    assert any("mismatch" in error.lower() for error in report["errors"])

    status = client.get("/api/ledger/status", headers=user["headers"])
    assert status.json()["tamper_detected"] is True


def test_ledger_scope_authorization(client, user_factory):
    creator = user_factory()
    create_registration(client, creator["headers"])
    assert client.get("/api/ledger/transactions?scope=all", headers=creator["headers"]).status_code == 403

    verifier = register_user(client, display_name="Ledger Verifier")
    with SessionLocal() as db:
        from app.models import User

        account = db.get(User, verifier["user"]["id"])
        account.role = "verifier"
        db.commit()
    assert client.get("/api/ledger/transactions?scope=all", headers=verifier["headers"]).status_code == 200


def test_audit_chain_detects_database_tampering(client, user_factory):
    user = user_factory()
    create_registration(client, user["headers"])

    valid = client.get("/api/audit-logs/verify", headers=user["headers"])
    assert valid.status_code == 200
    assert valid.json()["valid"] is True
    assert valid.json()["events"] >= 1

    with SessionLocal() as db:
        entry = db.query(AuditLog).order_by(AuditLog.created_at.asc()).first()
        entry.event_metadata = {"tampered": True}
        db.commit()

    invalid = client.get("/api/audit-logs/verify", headers=user["headers"])
    assert invalid.status_code == 200
    assert invalid.json()["valid"] is False
    assert invalid.json()["errors"]

    logs = client.get("/api/audit-logs", headers=user["headers"])
    assert logs.status_code == 200
    assert logs.json()["append_only"] is True
    assert logs.json()["total"] >= 1
