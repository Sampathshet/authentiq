import hashlib

from tests.helpers import create_registration, register_user


def test_registration_creates_fingerprint_commitment_and_ledger_record(client, user_factory):
    user = user_factory()
    created = create_registration(
        client,
        user["headers"],
        content=b"AUTHENTIQ registration payload",
        filename="payload.txt",
        title="Payload Study",
    )
    registration = created["registration"]

    assert created["ledger"]["mode"] == "simulation"
    assert created["ledger"]["simulated"] is True
    assert created["ledger"]["tx_id"]
    assert registration["sha256"] == hashlib.sha256(b"AUTHENTIQ registration payload").hexdigest()
    assert registration["commitment"].startswith("0x")
    assert len(registration["poseidon_commitment"]) == 66
    assert registration["ledger_mode"] == "simulation"
    assert registration["status"] == "registered"

    detail = client.get(f"/api/registrations/{registration['registration_id']}", headers=user["headers"])
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == registration["id"]
    assert body["metadata"]["chunk_count"] == created["upload"]["total_chunks"]
    assert body["version_count"] == 0
    assert body["has_private_access"] is True

    listing = client.get("/api/registrations", headers=user["headers"])
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["registration_id"] == registration["registration_id"]

    download = client.get(f"/api/registrations/{registration['registration_id']}/file", headers=user["headers"])
    assert download.status_code == 200
    assert download.content == created["content"]

    certificate = client.get(f"/api/registrations/{registration['registration_id']}/certificate", headers=user["headers"])
    assert certificate.status_code == 200
    assert certificate.headers["content-type"].startswith("application/pdf")
    assert certificate.content.startswith(b"%PDF")

    state = client.get(
        f"/api/registrations/{registration['registration_id']}/verification-state",
        headers=user["headers"],
    )
    assert state.status_code == 200
    record = state.json()["ledger_record"]
    assert record["mode"] == "simulation"
    assert record["payload_digest"] == record["payload_digest"].lower()
    assert len(record["record_hash"]) == 64


def test_duplicate_fingerprint_creates_alerts_for_both_owners(client, user_factory):
    first = user_factory(display_name="First Owner")
    second = user_factory(display_name="Second Owner")
    shared = b"byte-identical protected work"

    one = create_registration(client, first["headers"], content=shared, title="Original")
    assert one["alerts_created"] == 0
    two = create_registration(client, second["headers"], content=shared, title="Copy")
    assert two["alerts_created"] >= 2

    first_alerts = client.get("/api/alerts", headers=first["headers"])
    assert first_alerts.status_code == 200
    assert first_alerts.json()["total"] == 1
    alert = first_alerts.json()["items"][0]
    assert alert["alert_type"] == "exact_duplicate"
    assert alert["similarity_score"] == 1.0
    assert alert["registration_label"] == two["registration"]["registration_id"]
    assert alert["matched_label"] == one["registration"]["registration_id"]

    second_alerts = client.get("/api/alerts", headers=second["headers"])
    assert second_alerts.json()["total"] == 1
    assert second_alerts.json()["items"][0]["registration_label"] == two["registration"]["registration_id"]

    activity = client.get("/api/dashboard/activity", headers=first["headers"])
    assert activity.status_code == 200
    assert activity.json()["alerts"]


def test_duplicate_check_reports_existing_registration_before_upload(client, user_factory):
    owner = user_factory(display_name="First Owner")
    other = user_factory(display_name="Second Owner")
    shared = b"the very same protected document"
    digest = hashlib.sha256(shared).hexdigest()

    created = create_registration(client, owner["headers"], content=shared, title="Original Document")
    assert created["duplicates"]["exact_matches"] == []
    assert created["duplicates"]["similar_matches"] == []

    check = client.post(
        "/api/registrations/duplicate-check",
        headers=other["headers"],
        json={"sha256": digest},
    )
    assert check.status_code == 200
    report = check.json()
    assert report["checked"] is True
    assert len(report["exact_matches"]) == 1
    match = report["exact_matches"][0]
    assert match["registration_id"] == created["registration"]["registration_id"]
    assert match["similarity"] == 1.0
    assert match["method"] == "exact_sha256"
    assert match["owned_by_you"] is False
    assert match["same_organization"] is False

    own_check = client.post(
        "/api/registrations/duplicate-check",
        headers=owner["headers"],
        json={"sha256": digest},
    )
    assert own_check.status_code == 200
    assert own_check.json()["exact_matches"][0]["owned_by_you"] is True

    unique = client.post(
        "/api/registrations/duplicate-check",
        headers=other["headers"],
        json={"sha256": hashlib.sha256(b"a different document").hexdigest()},
    )
    assert unique.status_code == 200
    assert unique.json()["exact_matches"] == []

    second = create_registration(client, other["headers"], content=shared, title="Second Copy")
    assert len(second["duplicates"]["exact_matches"]) == 1
    assert second["duplicates"]["exact_matches"][0]["registration_id"] == created["registration"]["registration_id"]


def test_duplicate_check_requires_authentication(client):
    response = client.post("/api/registrations/duplicate-check", json={"sha256": "a" * 64})
    assert response.status_code == 401


def test_duplicate_check_rejects_invalid_fingerprint(client, user_factory):
    user = user_factory()
    response = client.post(
        "/api/registrations/duplicate-check",
        headers=user["headers"],
        json={"sha256": "not-a-fingerprint"},
    )
    assert response.status_code == 422


def test_registration_authorization_is_enforced(client, user_factory):
    owner = user_factory()
    stranger = register_user(client)
    created = create_registration(client, owner["headers"], title="Private Work")
    identifier = created["registration"]["registration_id"]

    assert client.get(f"/api/registrations/{identifier}", headers=stranger["headers"]).status_code == 403
    assert client.get(f"/api/registrations/{identifier}/file", headers=stranger["headers"]).status_code == 403
    assert client.get(f"/api/registrations/{identifier}/certificate", headers=stranger["headers"]).status_code == 403
    assert client.get(f"/api/registrations/{identifier}", headers=owner["headers"]).status_code == 200

    stranger_list = client.get("/api/registrations", headers=stranger["headers"])
    assert stranger_list.json()["total"] == 0

    public = client.get(f"/api/public/verify/{identifier}")
    assert public.status_code == 200
    assert public.json()["status"] == "private"
    assert public.json()["available"] is False


def test_registration_requires_completed_upload(client, user_factory):
    user = user_factory()
    response = client.post(
        "/api/registrations",
        headers=user["headers"],
        json={"upload_id": "missing-upload", "title": "Missing", "asset_type": "document"},
    )
    assert response.status_code == 404

    initiate = client.post(
        "/api/uploads/initiate",
        headers=user["headers"],
        json={
            "filename": "not-finished.txt",
            "size_bytes": 20,
            "mime_type": "text/plain",
            "total_chunks": 1,
            "chunk_size": 20,
        },
    )
    upload_id = initiate.json()["upload_id"]
    incomplete = client.post(
        "/api/registrations",
        headers=user["headers"],
        json={"upload_id": upload_id, "title": "Incomplete", "asset_type": "document"},
    )
    assert incomplete.status_code == 400


def test_dashboard_summary_uses_real_records(client, user_factory):
    user = user_factory()
    assert client.get("/api/dashboard/summary", headers=user["headers"]).json()["stats"]["total_creations"] == 0
    create_registration(client, user["headers"])
    summary = client.get("/api/dashboard/summary", headers=user["headers"])
    assert summary.status_code == 200
    stats = summary.json()["stats"]
    assert stats["total_creations"] == 1
    assert stats["verified_records"] == 0
    assert summary.json()["ledger"]["mode"] == "simulation"
