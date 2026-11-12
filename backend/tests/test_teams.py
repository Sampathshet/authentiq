import json

from tests.helpers import login_user, register_user


def _create_team(client, headers, name="Collective Work"):
    response = client.post("/api/teams", headers=headers, json={"name": name, "description": "Shared project"})
    assert response.status_code == 201, response.text
    return response.json()


def test_team_invite_join_and_unanimous_allocation(client, user_factory):
    owner = user_factory(display_name="Team Owner")
    collaborator = user_factory(display_name="Team Collaborator")
    team = _create_team(client, owner["headers"])
    assert team["member_count"] == 1
    assert team["my_role"] == "owner"
    assert team["members"][0]["ownership_percent"] == 100.0

    invite = client.post(
        f"/api/teams/{team['id']}/invite",
        headers=owner["headers"],
        json={"email": collaborator["email"], "role": "contributor"},
    )
    assert invite.status_code == 201, invite.text
    invite_body = invite.json()
    assert invite_body["invite_token"]
    assert invite_body["invite_url"].startswith(f"/teams/{team['id']}?invite=")
    assert "Email delivery is not configured" in invite_body["delivery"]

    duplicate_invite = client.post(
        f"/api/teams/{team['id']}/invite",
        headers=owner["headers"],
        json={"email": collaborator["email"], "role": "reviewer"},
    )
    assert duplicate_invite.status_code == 409

    pending_view = client.get(f"/api/teams/{team['id']}", headers=collaborator["headers"])
    assert pending_view.status_code == 200
    assert pending_view.json()["my_role"] == "contributor"

    join = client.post(
        f"/api/teams/{team['id']}/join",
        headers=collaborator["headers"],
        json={"token": invite_body["invite_token"]},
    )
    assert join.status_code == 200, join.text
    assert join.json()["member"]["status"] == "active"

    detail = client.get(f"/api/teams/{team['id']}", headers=owner["headers"]).json()
    members = {member["user_id"]: member for member in detail["members"]}
    owner_member = members[owner["user"]["id"]]
    collaborator_member = members[collaborator["user"]["id"]]

    invalid = client.post(
        f"/api/teams/{team['id']}/ownership/propose",
        headers=owner["headers"],
        json={
            "allocations": [
                {"member_id": owner_member["id"], "percent": 60},
                {"member_id": collaborator_member["id"], "percent": 30},
            ]
        },
    )
    assert invalid.status_code == 422
    assert "100" in invalid.json()["detail"]

    missing_member = client.post(
        f"/api/teams/{team['id']}/ownership/propose",
        headers=owner["headers"],
        json={"allocations": [{"member_id": owner_member["id"], "percent": 100}]},
    )
    assert missing_member.status_code == 422

    proposed = client.post(
        f"/api/teams/{team['id']}/ownership/propose",
        headers=owner["headers"],
        json={
            "allocations": [
                {"member_id": owner_member["id"], "percent": 60},
                {"member_id": collaborator_member["id"], "percent": 40},
            ]
        },
    )
    assert proposed.status_code == 200, proposed.text
    assert proposed.json()["total"] == 100.0

    owner_approval = client.post(
        f"/api/teams/{team['id']}/ownership/approve",
        headers=owner["headers"],
        json={"allocation_ids": []},
    )
    assert owner_approval.status_code == 200
    assert owner_approval.json()["approved"] is False

    collaborator_approval = client.post(
        f"/api/teams/{team['id']}/ownership/approve",
        headers=collaborator["headers"],
        json={"allocation_ids": []},
    )
    assert collaborator_approval.status_code == 200
    assert collaborator_approval.json()["approved"] is True
    ledger_tx_id = collaborator_approval.json()["ledger_tx_id"]
    assert ledger_tx_id

    final = client.get(f"/api/teams/{team['id']}/ownership", headers=owner["headers"])
    assert final.status_code == 200
    assert final.json()["status"] == "ownership_approved"
    percentages = sorted(item["percent"] for item in final.json()["allocations"] if item["status"] == "approved")
    assert percentages == [40.0, 60.0]
    assert round(sum(percentages), 2) == 100.0

    certificate = client.get(f"/api/teams/{team['id']}/certificate", headers=collaborator["headers"])
    assert certificate.status_code == 200
    evidence = json.loads(certificate.content)
    assert evidence["total_percent"] == 100.0
    assert evidence["ledger_mode"] == "simulation"
    assert len(evidence["allocations"]) == 2


def test_team_roles_and_membership_authorization(client, user_factory):
    owner = user_factory(display_name="Owner")
    outsider = register_user(client, display_name="Outsider")
    team = _create_team(client, owner["headers"], name="Private Collective")

    assert client.get(f"/api/teams/{team['id']}", headers=outsider["headers"]).status_code == 403
    assert client.post(
        f"/api/teams/{team['id']}/invite",
        headers=outsider["headers"],
        json={"email": outsider["email"], "role": "contributor"},
    ).status_code == 403
    assert client.post(
        f"/api/teams/{team['id']}/ownership/propose",
        headers=outsider["headers"],
        json={"allocations": []},
    ).status_code == 403
    assert client.get(f"/api/teams/{team['id']}/certificate", headers=owner["headers"]).status_code == 409

    teams = client.get("/api/teams", headers=outsider["headers"])
    assert teams.status_code == 200
    assert teams.json()["items"] == []


def test_only_project_owner_can_propose_allocation(client, user_factory):
    owner = user_factory()
    collaborator = user_factory()
    team = _create_team(client, owner["headers"])
    invite = client.post(
        f"/api/teams/{team['id']}/invite",
        headers=owner["headers"],
        json={"email": collaborator["email"], "role": "co_owner"},
    ).json()
    client.post(
        f"/api/teams/{team['id']}/join",
        headers=collaborator["headers"],
        json={"token": invite["invite_token"]},
    )
    members = client.get(f"/api/teams/{team['id']}", headers=owner["headers"]).json()["members"]
    payload = {
        "allocations": [
            {"member_id": member["id"], "percent": 50}
            for member in members
        ]
    }
    response = client.post(
        f"/api/teams/{team['id']}/ownership/propose",
        headers=collaborator["headers"],
        json=payload,
    )
    assert response.status_code == 403
    assert "owner" in response.json()["detail"].lower()

    relogged = login_user(client, collaborator["email"])
    assert client.get("/api/teams", headers=relogged["headers"]).json()["items"][0]["id"] == team["id"]
