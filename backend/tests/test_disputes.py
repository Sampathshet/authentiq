from app.core.database import SessionLocal
from app.models import User
from tests.helpers import create_registration, register_user


def _make_verifier(client):
    verifier = register_user(client, display_name="Dispute Reviewer")
    with SessionLocal() as db:
        account = db.get(User, verifier["user"]["id"])
        account.role = "verifier"
        db.commit()
    return verifier


def test_dispute_lifecycle_with_evidence_and_verifier_resolution(client, user_factory):
    owner = user_factory(display_name="Disputed Owner")
    claimant = user_factory(display_name="Claimant")
    outsider = register_user(client, display_name="No Access")
    verifier = _make_verifier(client)
    created = create_registration(client, owner["headers"], content=b"disputed work", title="Disputed Work")
    identifier = created["registration"]["registration_id"]

    dispute_response = client.post(
        "/api/disputes",
        headers=claimant["headers"],
        json={
            "registration_id": identifier,
            "reason": "prior_creation",
            "description": "I published a substantively identical work before this registration date.",
        },
    )
    assert dispute_response.status_code == 201, dispute_response.text
    dispute = dispute_response.json()
    assert dispute["status"] == "open"
    assert dispute["respondent_id"] == owner["user"]["id"]
    assert dispute["earliest_registration_id"] == identifier

    duplicate = client.post(
        "/api/disputes",
        headers=claimant["headers"],
        json={
            "registration_id": identifier,
            "reason": "prior_creation",
            "description": "A second active dispute should not be accepted.",
        },
    )
    assert duplicate.status_code == 409

    owner_view = client.get(f"/api/disputes/{dispute['id']}", headers=owner["headers"])
    assert owner_view.status_code == 200
    assert owner_view.json()["can_upload_evidence"] is True
    assert owner_view.json()["registration"]["sha256"] == created["registration"]["sha256"]

    assert client.get(f"/api/disputes/{dispute['id']}", headers=outsider["headers"]).status_code == 403

    evidence = client.post(
        f"/api/disputes/{dispute['id']}/evidence",
        headers=claimant["headers"],
        params={"description": "Earlier draft"},
        files={"file": ("earlier-draft.txt", b"earlier draft contents", "text/plain")},
    )
    assert evidence.status_code == 201, evidence.text

    detail = client.get(f"/api/disputes/{dispute['id']}", headers=owner["headers"]).json()
    assert len(detail["evidence"]) == 1
    evidence_id = detail["evidence"][0]["id"]
    download = client.get(f"/api/disputes/{dispute['id']}/evidence/{evidence_id}", headers=owner["headers"])
    assert download.status_code == 200
    assert download.content == b"earlier draft contents"

    under_review = client.post(
        f"/api/disputes/{dispute['id']}/status",
        headers=claimant["headers"],
        json={"status": "under_review"},
    )
    assert under_review.status_code == 200
    assert under_review.json()["status"] == "under_review"

    claimant_finalize = client.post(
        f"/api/disputes/{dispute['id']}/status",
        headers=claimant["headers"],
        json={"status": "resolved", "resolution": "Claimant cannot self-resolve."},
    )
    assert claimant_finalize.status_code == 403

    missing_resolution = client.post(
        f"/api/disputes/{dispute['id']}/status",
        headers=verifier["headers"],
        json={"status": "resolved"},
    )
    assert missing_resolution.status_code == 422

    resolved = client.post(
        f"/api/disputes/{dispute['id']}/status",
        headers=verifier["headers"],
        json={
            "status": "resolved",
            "resolution": "Evidence reviewed. Registration remains on record with a dispute annotation.",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"

    final = client.get(f"/api/disputes/{dispute['id']}", headers=claimant["headers"]).json()
    assert final["status"] == "resolved"
    assert final["resolved_at"]
    assert final["can_review"] is False

    verifier_list = client.get("/api/disputes", headers=verifier["headers"])
    assert verifier_list.status_code == 200
    assert verifier_list.json()["items"][0]["id"] == dispute["id"]

    report = client.get(f"/api/disputes/{dispute['id']}/report", headers=claimant["headers"])
    assert report.status_code == 200
    body = report.json()
    assert body["format"] == "AUTHENTIQ-DISPUTE-EVIDENCE-REPORT-V1"
    assert body["registration_priority"]["earliest_registration_id"] == identifier
    assert "not an automatic legal determination" in body["registration_priority"]["interpretation"]
    assert body["ledger"]["mode"] == "simulation"
    assert body["audit_chain"]["valid"] is True
    assert len(body["evidence"]) == 1

    registration = client.get(f"/api/registrations/{identifier}", headers=owner["headers"])
    assert registration.status_code == 200
    assert registration.json()["status"] == "verified"


def test_outside_party_cannot_resolve_dispute(client, user_factory):
    owner = user_factory()
    claimant = user_factory()
    outsider = register_user(client)
    identifier = create_registration(client, owner["headers"])["registration"]["registration_id"]
    dispute = client.post(
        "/api/disputes",
        headers=claimant["headers"],
        json={
            "registration_id": identifier,
            "reason": "unauthorized_resolution_attempt",
            "description": "This dispute exists to verify reviewer authorization boundaries.",
        },
    ).json()

    response = client.post(
        f"/api/disputes/{dispute['id']}/status",
        headers=outsider["headers"],
        json={"status": "resolved", "resolution": "Should not be permitted."},
    )
    assert response.status_code == 403
    assert client.get(f"/api/disputes/{dispute['id']}", headers=outsider["headers"]).status_code == 403
