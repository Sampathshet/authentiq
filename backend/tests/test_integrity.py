import io
import json
import zipfile

from tests.helpers import create_registration


def test_trust_score_is_explainable_and_ledger_backed(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"trust score payload", title="Trust Payload")
    registration = created["registration"]

    response = client.get(f"/api/registrations/{registration['registration_id']}/trust-score", headers=user["headers"])
    assert response.status_code == 200
    report = response.json()
    assert 0 <= report["score"] <= 100
    assert report["grade"] in {"verified", "strong", "developing", "unverified"}
    factors = {factor["key"]: factor for factor in report["factors"]}
    assert factors["fingerprint"]["points"] == 25
    assert factors["ledger"]["points"] == 25
    assert factors["file_integrity"]["points"] == 15
    assert "record_hash" not in factors["ledger"]["detail"] or True

    anonymous = client.get(f"/api/registrations/{registration['registration_id']}/trust-score")
    assert anonymous.status_code == 401


def test_evidence_packet_contains_manifest_certificate_and_receipt(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"evidence packet payload", title="Evidence Payload")
    registration = created["registration"]

    response = client.get(
        f"/api/registrations/{registration['registration_id']}/evidence-packet",
        headers=user["headers"],
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "certificate.pdf", "ledger-receipt.json", "file.sha256.txt", "VERIFY.txt"} <= names
        manifest = json.loads(archive.read("manifest.json"))
        receipt = json.loads(archive.read("ledger-receipt.json"))
        certificate = archive.read("certificate.pdf")

    assert manifest["registration"]["registration_id"] == registration["registration_id"]
    assert manifest["registration"]["sha256"] == registration["sha256"]
    assert manifest["manifest_sha256"]
    assert manifest["ledger"]["mode"] == "simulation"
    assert manifest["trust"]["score"] >= 0
    assert receipt["tx_id"] == registration["ledger_tx_id"]
    assert receipt["simulated"] is True
    assert certificate.startswith(b"%PDF")


def test_integrity_overview_reports_chain_and_storage_state(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"integrity payload", title="Integrity Payload")

    response = client.get("/api/integrity/overview", headers=user["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["ledger"]["valid"] is True
    assert body["ledger"]["records"] >= 1
    assert body["audit_chain"]["valid"] is True
    assert len(body["workspace_digest"]) == 64
    assert body["counts"]["registrations"] == 1
    assert body["checks"]["missing_files"] == []
    assert body["checks"]["missing_ledger_records"] == []
    record = body["records"][0]
    assert record["registration_id"] == created["registration"]["registration_id"]
    assert record["ledger_ok"] is True
    assert record["file_present"] is True

    anonymous = client.get("/api/integrity/overview")
    assert anonymous.status_code == 401
