from tests.helpers import register_user


def create_team(client, headers, name="Redeem Studio"):
    response = client.post("/api/teams", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def invite(client, owner_headers, project_id, email, role="contributor"):
    response = client.post(
        f"/api/teams/{project_id}/invite",
        headers=owner_headers,
        json={"email": email, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_invitee_can_redeem_code_with_any_account(client, user_factory):
    owner = user_factory()
    team = create_team(client, owner["headers"])
    invitation = invite(client, owner["headers"], team["id"], "invitee@authentiq.dev")
    token = invitation["invite_token"]

    redeemer = register_user(client, display_name="Redeemer")
    redeemed = client.post("/api/teams/redeem", headers=redeemer["headers"], json={"token": token})
    assert redeemed.status_code == 200, redeemed.text
    payload = redeemed.json()
    assert payload["project_id"] == team["id"]
    assert payload["member"]["status"] == "active"

    detail = client.get(f"/api/teams/{team['id']}", headers=redeemer["headers"])
    assert detail.status_code == 200
    assert detail.json()["my_status"] == "active"

    reused = client.post("/api/teams/redeem", headers=owner["headers"], json={"token": token})
    assert reused.status_code == 404


def test_pending_invitation_is_listed_for_invited_email(client, user_factory):
    owner = user_factory()
    team = create_team(client, owner["headers"])
    invitee = register_user(client, display_name="Invitee")
    email = invitee["user"]["email"]
    invite(client, owner["headers"], team["id"], email, role="reviewer")

    listing = client.get("/api/teams", headers=invitee["headers"])
    assert listing.status_code == 200
    items = listing.json()["items"]
    match = next(item for item in items if item["id"] == team["id"])
    assert match["my_status"] == "invited"

    joined = client.post(f"/api/teams/{team['id']}/join", headers=invitee["headers"], json={})
    assert joined.status_code == 200, joined.text
    assert joined.json()["member"]["status"] == "active"


def test_invite_link_opens_project_for_token_holder(client, user_factory):
    owner = user_factory()
    team = create_team(client, owner["headers"])
    invitation = invite(client, owner["headers"], team["id"], "link@authentiq.dev")
    token = invitation["invite_token"]

    visitor = register_user(client, display_name="Visitor")
    opened = client.get(f"/api/teams/{team['id']}?invite={token}", headers=visitor["headers"])
    assert opened.status_code == 200, opened.text

    denied = client.get(f"/api/teams/{team['id']}", headers=visitor["headers"])
    assert denied.status_code == 403
