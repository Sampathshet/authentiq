"""Site administration console and organization invitation flow."""

import hashlib

from app.core.database import SessionLocal
from app.models import User
from tests.helpers import create_registration, register_user

PASSWORD = "Authentiq!Test2026"


def _set_role(user_id: str, role: str) -> None:
    with SessionLocal() as db:
        account = db.get(User, user_id)
        account.role = role
        db.commit()


def _register_creation(client, headers, content=b"organization scope sample", title="Scoped", scope=None):
    sha = hashlib.sha256(content).hexdigest()
    initiate = client.post(
        "/api/uploads/initiate",
        headers=headers,
        json={
            "filename": "scoped.txt",
            "size_bytes": len(content),
            "mime_type": "text/plain",
            "total_chunks": 1,
            "chunk_size": 65536,
        },
    ).json()
    client.post(
        f"/api/uploads/{initiate['upload_id']}/chunk",
        headers=headers,
        data={"chunk_index": "0", "sha256": sha},
        files={"file": ("scoped.txt", content, "text/plain")},
    )
    client.post(f"/api/uploads/{initiate['upload_id']}/complete", headers=headers, data={"client_sha256": sha})
    payload = {
        "upload_id": initiate["upload_id"],
        "title": title,
        "asset_type": "document",
        "privacy": "private",
    }
    if scope is not None:
        payload["scope_to_organization"] = scope
    response = client.post("/api/registrations", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["registration"]


def test_site_admin_console_is_role_guarded(client, user_factory):
    user = user_factory(display_name="Regular Creator")
    assert client.get("/api/admin/overview", headers=user["headers"]).status_code == 403
    assert client.get("/api/admin/users", headers=user["headers"]).status_code == 403

    _set_role(user["user"]["id"], "site_admin")
    overview = client.get("/api/admin/overview", headers=user["headers"])
    assert overview.status_code == 200, overview.text
    stats = overview.json()["stats"]
    assert stats["users"] >= 1
    assert "organizations" in stats
    assert "open_disputes" in stats

    listing = client.get("/api/admin/users", headers=user["headers"])
    assert listing.status_code == 200
    assert any(item["email"] == user["email"] for item in listing.json()["items"])

    assert client.get("/api/admin/organizations", headers=user["headers"]).status_code == 200
    assert client.get("/api/admin/registrations", headers=user["headers"]).status_code == 200
    assert client.get("/api/admin/teams", headers=user["headers"]).status_code == 200
    assert client.get("/api/admin/audit", headers=user["headers"]).status_code == 200
    assert client.get("/api/admin/disputes", headers=user["headers"]).status_code == 200


def test_site_admin_can_control_accounts(client, user_factory):
    admin_user = user_factory(display_name="Site Admin")
    _set_role(admin_user["user"]["id"], "site_admin")
    target = user_factory(display_name="Managed Creator")

    promoted = client.patch(
        f"/api/admin/users/{target['user']['id']}",
        headers=admin_user["headers"],
        json={"role": "verifier"},
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["user"]["role"] == "verifier"

    suspended = client.patch(
        f"/api/admin/users/{target['user']['id']}",
        headers=admin_user["headers"],
        json={"is_active": False},
    )
    assert suspended.status_code == 200
    assert suspended.json()["user"]["is_active"] is False
    assert client.get("/api/dashboard/summary", headers=target["headers"]).status_code == 401

    self_suspend = client.patch(
        f"/api/admin/users/{admin_user['user']['id']}",
        headers=admin_user["headers"],
        json={"is_active": False},
    )
    assert self_suspend.status_code == 422


def test_organization_invitation_grants_workspace_access(client, user_factory):
    owner = user_factory(display_name="Org Owner", account_type="organization", organization_name="Northwind Studio")
    invitee = user_factory(display_name="Invited Member")

    organization = client.get("/api/settings/organization", headers=owner["headers"]).json()
    assert organization["organization"] is not None
    assert organization["can_manage"] is True

    created = client.post(
        "/api/settings/organization/invitations",
        headers=owner["headers"],
        json={"email": invitee["email"], "display_name": "Invited Member", "role": "org_member"},
    )
    assert created.status_code == 201, created.text
    invitation = created.json()["invitation"]
    assert invitation["status"] == "invited"
    assert invitation["invite_url"].startswith("/join?code=")

    # A non-admin cannot issue organization invitations.
    assert client.post(
        "/api/settings/organization/invitations",
        headers=invitee["headers"],
        json={"email": "someone@authentiq.dev"},
    ).status_code in (403, 404)

    accepted = client.post(
        "/api/settings/organization/invitations/accept",
        headers=invitee["headers"],
        json={"token": invitation["invite_token"]},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["organization"]["name"] == organization["organization"]["name"]

    # The invitation cannot be redeemed twice.
    assert client.post(
        "/api/settings/organization/invitations/accept",
        headers=invitee["headers"],
        json={"token": invitation["invite_token"]},
    ).status_code == 404

    members = client.get("/api/settings/organization", headers=owner["headers"]).json()
    assert any(member["email"] == invitee["email"] for member in members["members"])


def test_account_can_create_its_own_organization(client, user_factory):
    user = user_factory(display_name="Solo Founder")

    assert client.get("/api/settings/organization", headers=user["headers"]).json()["organization"] is None

    created = client.post(
        "/api/settings/organization",
        headers=user["headers"],
        json={"name": "Foundry Works"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["organization"]["name"] == "Foundry Works"
    assert created.json()["role"] == "org_admin"

    duplicate = client.post(
        "/api/settings/organization",
        headers=user["headers"],
        json={"name": "Foundry Works"},
    )
    assert duplicate.status_code == 409

    organization = client.get("/api/settings/organization", headers=user["headers"]).json()
    assert organization["organization"]["name"] == "Foundry Works"
    assert organization["can_manage"] is True

    # The account can now register organization-owned creations.
    registration = _register_creation(client, user["headers"], content=b"new org work", title="Org Work", scope=True)
    assert registration["organization_id"] == organization["organization"]["id"]


def test_organization_registrations_follow_the_toggle(client, user_factory):
    owner = user_factory(display_name="Org Owner", account_type="organization", organization_name="Northwind Studio")
    invitee = user_factory(display_name="Invited Member")
    invitation = client.post(
        "/api/settings/organization/invitations",
        headers=owner["headers"],
        json={"email": invitee["email"], "role": "org_member"},
    ).json()["invitation"]
    client.post(
        "/api/settings/organization/invitations/accept",
        headers=invitee["headers"],
        json={"token": invitation["invite_token"]},
    )

    shared = _register_creation(client, invitee["headers"], content=b"shared organization work", title="Shared", scope=True)
    personal = _register_creation(client, invitee["headers"], content=b"personal only work", title="Personal", scope=False)

    organization_id = client.get("/api/settings/organization", headers=invitee["headers"]).json()["organization"]["id"]
    assert shared["organization_id"] == organization_id
    assert personal["organization_id"] is None

    listing = client.get("/api/settings/organization/registrations", headers=invitee["headers"]).json()
    titles = [item["title"] for item in listing["items"]]
    assert "Shared" in titles
    assert "Personal" not in titles
    assert listing["total"] >= 1

    # A member of the organization can open the shared record.
    assert client.get(f"/api/registrations/{shared['registration_id']}", headers=owner["headers"]).status_code == 200
