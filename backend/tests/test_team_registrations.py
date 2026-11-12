from tests.helpers import create_registration, register_user, upload_file


def _team(client, headers, name="Studio Nova"):
    response = client.post("/api/teams", headers=headers, json={"name": name, "description": "Team workspace"})
    assert response.status_code == 201, response.text
    return response.json()


def _invite_member(client, owner_headers, email):
    response = client.post(
        f"/api/teams/{owner_headers['team_id']}/invite",
        headers=owner_headers,
        json={"email": email, "role": "contributor"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_registration_can_be_attributed_to_a_team(client, user_factory):
    owner = user_factory(display_name="Team Owner")
    team = _team(client, owner["headers"])
    owner["headers"]["team_id"] = team["id"]

    created = create_registration(
        client,
        owner["headers"],
        title="Team Poster",
        privacy="public",
        asset_type="design",
        team_id=team["id"],
    )
    registration = created["registration"]

    assert registration["team_id"] == team["id"]
    assert registration["team_name"] == team["name"]
    assert created["team"]["name"] == team["name"]
    assert created["team"]["allocation_status"] is None
    assert created["team"]["members"][0]["name"] == "Team Owner"

    detail = client.get(f"/api/registrations/{registration['id']}", headers=owner["headers"])
    assert detail.status_code == 200
    body = detail.json()
    assert body["team"]["name"] == team["name"]
    assert body["team_membership"]["role"] == "owner"


def test_team_members_can_read_team_creations(client, user_factory):
    owner = user_factory(display_name="Team Owner")
    team = _team(client, owner["headers"])
    owner["headers"]["team_id"] = team["id"]

    member = user_factory(display_name="Team Member")
    invite = _invite_member(client, owner["headers"], member["email"])
    joined = client.post(
        f"/api/teams/{team['id']}/join",
        headers=member["headers"],
        json={"token": invite["invite_token"]},
    )
    assert joined.status_code == 200, joined.text

    created = create_registration(client, owner["headers"], title="Shared Asset", team_id=team["id"])
    registration = created["registration"]

    # The member did not register it, but team membership grants read access.
    detail = client.get(f"/api/registrations/{registration['id']}", headers=member["headers"])
    assert detail.status_code == 200
    assert detail.json()["team"]["name"] == team["name"]

    workspace = client.get(f"/api/teams/{team['id']}", headers=member["headers"])
    assert workspace.status_code == 200
    creations = workspace.json()["creations"]
    assert len(creations) == 1
    assert creations[0]["registration_id"] == registration["registration_id"]
    assert creations[0]["owner_name"] == "Team Owner"

    listing = client.get("/api/registrations", headers=member["headers"])
    assert listing.status_code == 200
    assert any(item["registration_id"] == registration["registration_id"] for item in listing.json()["items"])


def test_non_member_cannot_attach_or_read_team_creations(client, user_factory):
    owner = user_factory(display_name="Team Owner")
    team = _team(client, owner["headers"])
    owner["headers"]["team_id"] = team["id"]
    created = create_registration(client, owner["headers"], title="Closed Asset", team_id=team["id"])

    outsider = user_factory(display_name="Outsider")
    upload = upload_file(client, outsider["headers"], b"hello", filename="x.txt")
    rejected = client.post(
        "/api/registrations",
        headers=outsider["headers"],
        json={
            "upload_id": upload["upload_id"],
            "title": "Snapped In",
            "privacy": "private",
            "team_id": team["id"],
        },
    )
    assert rejected.status_code == 400
    assert "not an active member" in rejected.json()["detail"]

    blocked = client.get(
        f"/api/registrations/{created['registration']['id']}", headers=outsider["headers"]
    )
    assert blocked.status_code == 403


def test_public_registry_credits_the_team(client, user_factory):
    owner = user_factory(display_name="Team Owner")
    team = _team(client, owner["headers"])
    owner["headers"]["team_id"] = team["id"]
    create_registration(
        client, owner["headers"], title="Public Team Work", privacy="public", team_id=team["id"]
    )

    listing = client.get("/api/public/records")
    assert listing.status_code == 200
    item = listing.json()["items"][0]
    assert item["team_name"] == team["name"]
    assert item["creator_name"] == "Team Owner"

    by_team = client.get("/api/public/records", params={"q": "Studio Nova"})
    assert by_team.status_code == 200
    assert by_team.json()["total"] == 1
