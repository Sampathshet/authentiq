from tests.helpers import create_registration, register_user


def test_two_party_transfer_completes_and_moves_access(client, user_factory):
    owner = user_factory(display_name="Current Owner")
    recipient = user_factory(display_name="Next Owner")
    outsider = register_user(client, display_name="Unrelated")
    created = create_registration(client, owner["headers"], content=b"ownership transfer subject", title="Transferable")
    registration = created["registration"]
    identifier = registration["registration_id"]

    self_transfer = client.post(
        "/api/transfers",
        headers=owner["headers"],
        json={"registration_id": identifier, "recipient_email": owner["email"], "reason": "test"},
    )
    assert self_transfer.status_code == 422

    unknown = client.post(
        "/api/transfers",
        headers=owner["headers"],
        json={"registration_id": identifier, "recipient_email": "nobody@authentiq.dev"},
    )
    assert unknown.status_code == 404

    created_transfer = client.post(
        "/api/transfers",
        headers=owner["headers"],
        json={"registration_id": identifier, "recipient_email": recipient["email"], "reason": "Collaboration handoff"},
    )
    assert created_transfer.status_code == 201, created_transfer.text
    transfer = created_transfer.json()
    assert transfer["status"] == "pending_recipient"
    assert transfer["to_user_id"] == recipient["user"]["id"]

    duplicate = client.post(
        "/api/transfers",
        headers=owner["headers"],
        json={"registration_id": identifier, "recipient_email": recipient["email"]},
    )
    assert duplicate.status_code == 409

    unauthorized = client.post(f"/api/transfers/{transfer['id']}/accept", headers=outsider["headers"])
    assert unauthorized.status_code == 403

    accepted = client.post(f"/api/transfers/{transfer['id']}/accept", headers=recipient["headers"])
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "recipient_accepted"

    recipient_confirm = client.post(f"/api/transfers/{transfer['id']}/confirm", headers=recipient["headers"])
    assert recipient_confirm.status_code == 403

    confirmed = client.post(f"/api/transfers/{transfer['id']}/confirm", headers=owner["headers"])
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "completed"
    assert confirmed.json()["ledger_tx_id"]

    assert client.get(f"/api/registrations/{identifier}", headers=recipient["headers"]).status_code == 200
    assert client.get(f"/api/registrations/{identifier}", headers=owner["headers"]).status_code == 403
    assert client.get(f"/api/registrations/{identifier}/file", headers=recipient["headers"]).content == created["content"]

    history = client.get(f"/api/transfers/history/{identifier}", headers=recipient["headers"])
    assert history.status_code == 200
    assert history.json()["chain_of_ownership_is_append_only"] is True
    assert history.json()["registration"]["current_owner_id"] == recipient["user"]["id"]
    assert history.json()["items"][-1]["status"] == "completed"

    outgoing = client.get("/api/transfers?direction=outgoing", headers=owner["headers"])
    incoming = client.get("/api/transfers?direction=incoming", headers=recipient["headers"])
    assert outgoing.json()["items"][0]["id"] == transfer["id"]
    assert incoming.json()["items"][0]["id"] == transfer["id"]


def test_recipient_can_reject_and_owner_can_cancel(client, user_factory):
    owner = user_factory()
    recipient = user_factory()
    rejected_registration = create_registration(client, owner["headers"], title="Rejected Transfer")["registration"]
    transfer = client.post(
        "/api/transfers",
        headers=owner["headers"],
        json={"registration_id": rejected_registration["registration_id"], "recipient_email": recipient["email"]},
    ).json()
    rejected = client.post(
        f"/api/transfers/{transfer['id']}/reject",
        headers=recipient["headers"],
        json={"reason": "Not the right owner"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Not the right owner"
    assert client.get(
        f"/api/registrations/{rejected_registration['registration_id']}",
        headers=owner["headers"],
    ).status_code == 200

    cancelled_registration = create_registration(client, owner["headers"], title="Cancelled Transfer")["registration"]
    transfer = client.post(
        "/api/transfers",
        headers=owner["headers"],
        json={"registration_id": cancelled_registration["registration_id"], "recipient_email": recipient["email"]},
    ).json()
    cancelled = client.post(f"/api/transfers/{transfer['id']}/cancel", headers=owner["headers"])
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.get(
        f"/api/registrations/{cancelled_registration['registration_id']}",
        headers=owner["headers"],
    ).status_code == 200
