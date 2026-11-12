"""Ownership transfer behaviour: pending visibility, handover, credential rotation."""

from app.core.database import SessionLocal
from app.models import Registration
from app.services.access import secret_for
from app.zkp.sigma import generate_proof
from tests.helpers import create_registration, register_user


def _start_transfer(client, owner, recipient, registration_id):
    response = client.post(
        "/api/transfers",
        headers=owner["headers"],
        json={"registration_id": registration_id, "recipient_email": recipient["email"], "reason": "handover"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _secret_snapshot(registration_id: str) -> tuple[int, int]:
    with SessionLocal() as db:
        registration = db.get(Registration, registration_id)
        return secret_for(registration)


def test_pending_recipient_sees_the_record_and_all_file_data(client, user_factory):
    owner = user_factory(display_name="Outgoing Owner")
    recipient = user_factory(display_name="Incoming Owner")
    created = create_registration(client, owner["headers"], content=b"pending transfer payload", title="Pending Handover")
    registration = created["registration"]

    transfer = _start_transfer(client, owner, recipient, registration["registration_id"])

    # The recipient can open the record and read the encrypted original.
    detail = client.get(f"/api/registrations/{registration['registration_id']}", headers=recipient["headers"])
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["ownership"]["status"] == "pending_confirmation"
    assert body["ownership"]["pending_transfer"]["id"] == transfer["id"]
    assert body["ownership"]["pending_transfer"]["awaiting"] == "recipient_response"
    assert body["file"]["size_bytes"] == len(created["content"])
    assert body["file"]["stored"] is True
    assert body["sha256"] == registration["sha256"]

    download = client.get(f"/api/registrations/{registration['registration_id']}/file", headers=recipient["headers"])
    assert download.status_code == 200
    assert download.content == created["content"]

    # It shows up in the recipient's workspace with the pending flag.
    listing = client.get("/api/registrations", headers=recipient["headers"])
    assert listing.status_code == 200
    pending_items = [item for item in listing.json()["items"] if item["registration_id"] == registration["registration_id"]]
    assert pending_items, "pending record must appear in the recipient workspace"
    assert pending_items[0]["ownership_status"] == "pending_confirmation"

    # Owner-only actions stay locked while the current owner still holds ownership.
    key = client.get(f"/api/registrations/{registration['registration_id']}/verification-key", headers=recipient["headers"])
    assert key.status_code == 403
    share = client.post(
        "/api/sharing/create",
        headers=recipient["headers"],
        json={"registration_id": registration["registration_id"]},
    )
    assert share.status_code == 403
    new_transfer = client.post(
        "/api/transfers",
        headers=recipient["headers"],
        json={"registration_id": registration["registration_id"], "recipient_email": owner["email"]},
    )
    assert new_transfer.status_code == 403


def test_completed_transfer_reflects_in_new_owner_workspace(client, user_factory):
    owner = user_factory(display_name="First Owner")
    recipient = user_factory(display_name="Second Owner")
    created = create_registration(client, owner["headers"], content=b"completed transfer payload", title="Completed Handover")
    registration = created["registration"]

    transfer = _start_transfer(client, owner, recipient, registration["registration_id"])
    assert client.post(f"/api/transfers/{transfer['id']}/accept", headers=recipient["headers"]).status_code == 200

    accepted = client.get(f"/api/registrations/{registration['registration_id']}", headers=recipient["headers"]).json()
    assert accepted["ownership"]["status"] == "pending_confirmation"
    assert accepted["ownership"]["pending_transfer"]["awaiting"] == "owner_confirmation"

    confirmed = client.post(f"/api/transfers/{transfer['id']}/confirm", headers=owner["headers"])
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "completed"
    assert confirmed.json()["credential_rotated"] is True

    # The record now belongs to the recipient in their own workspace.
    listing = client.get("/api/registrations", headers=recipient["headers"]).json()
    owned = [item for item in listing["items"] if item["registration_id"] == registration["registration_id"]]
    assert owned
    assert owned[0]["ownership_status"] == "owned"

    detail = client.get(f"/api/registrations/{registration['registration_id']}", headers=recipient["headers"]).json()
    assert detail["ownership"]["status"] == "owned"
    assert detail["ownership"]["current_owner_id"] == recipient["user"]["id"]
    assert detail["ownership"]["transfer_count"] == 1
    assert detail["ownership"]["credential_rotations"] == 1
    assert detail["file"]["size_bytes"] == len(created["content"])

    # The previous owner loses access.
    assert client.get(f"/api/registrations/{registration['registration_id']}", headers=owner["headers"]).status_code == 403

    # The chain of ownership is visible to the new owner.
    chain = client.get(f"/api/registrations/{registration['registration_id']}/ownership-chain", headers=recipient["headers"])
    assert chain.status_code == 200
    payload = chain.json()
    assert payload["append_only"] is True
    kinds = [event["kind"] for event in payload["events"]]
    assert kinds == ["registered", "transfer"]
    assert payload["events"][1]["status"] == "completed"
    assert payload["events"][1]["is_current"] is True
    assert payload["current_owner_id"] == recipient["user"]["id"]


def test_ownership_credential_rotates_on_transfer(client, user_factory):
    owner = user_factory(display_name="Rotating Owner")
    recipient = user_factory(display_name="Rotated Owner")
    created = create_registration(client, owner["headers"], content=b"credential rotation payload")
    registration = created["registration"]
    identifier = registration["registration_id"]

    old_key = created["verification_key"]
    old_secret, old_blinding = _secret_snapshot(registration["id"])

    transfer = _start_transfer(client, owner, recipient, identifier)
    client.post(f"/api/transfers/{transfer['id']}/accept", headers=recipient["headers"])
    client.post(f"/api/transfers/{transfer['id']}/confirm", headers=owner["headers"])

    new_key = client.get(f"/api/registrations/{identifier}/verification-key", headers=recipient["headers"])
    assert new_key.status_code == 200
    assert new_key.json()["verification_key"] != old_key

    new_secret, new_blinding = _secret_snapshot(registration["id"])

    challenge = client.post(
        "/api/public/verify/anonymous/challenge",
        json={"registration_id": identifier, "file_sha256": registration["sha256"]},
    )
    assert challenge.status_code == 200
    nonce = challenge.json()["nonce"]
    challenge_id = challenge.json()["challenge_id"]
    commitment = client.get(f"/api/registrations/{identifier}", headers=recipient["headers"]).json()["commitment"]

    stale_proof = generate_proof(registration["sha256"], identifier, nonce, commitment, old_secret, old_blinding)
    stale = client.post(
        "/api/public/verify/anonymous/verify",
        json={"challenge_id": challenge_id, "proof": stale_proof},
    )
    assert stale.status_code == 200
    assert stale.json()["valid"] is False
    assert stale.json()["checks"]["proof_valid"] is False

    fresh_challenge = client.post(
        "/api/public/verify/anonymous/challenge",
        json={"registration_id": identifier, "file_sha256": registration["sha256"]},
    ).json()
    fresh_proof = generate_proof(
        registration["sha256"],
        identifier,
        fresh_challenge["nonce"],
        commitment,
        new_secret,
        new_blinding,
    )
    fresh = client.post(
        "/api/public/verify/anonymous/verify",
        json={"challenge_id": fresh_challenge["challenge_id"], "proof": fresh_proof},
    )
    assert fresh.status_code == 200
    assert fresh.json()["valid"] is True
    assert fresh.json()["checks"]["private_key_disclosed"] is False


def test_rejected_transfer_leaves_ownership_untouched(client, user_factory):
    owner = user_factory()
    recipient = user_factory()
    outsider = register_user(client, display_name="Unrelated")
    created = create_registration(client, owner["headers"])
    registration = created["registration"]

    transfer = _start_transfer(client, owner, recipient, registration["registration_id"])
    rejected = client.post(
        f"/api/transfers/{transfer['id']}/reject",
        headers=recipient["headers"],
        json={"reason": "Not the right owner"},
    )
    assert rejected.status_code == 200

    listing = client.get("/api/registrations", headers=recipient["headers"]).json()
    assert not [item for item in listing["items"] if item["registration_id"] == registration["registration_id"]]
    assert client.get(f"/api/registrations/{registration['registration_id']}", headers=recipient["headers"]).status_code == 403
    assert client.get(f"/api/registrations/{registration['registration_id']}", headers=owner["headers"]).status_code == 200
    assert client.get(f"/api/registrations/{registration['registration_id']}", headers=outsider["headers"]).status_code == 403
