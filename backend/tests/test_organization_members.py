from tests.helpers import login_user


def add_member(client, headers, email, display_name="New Collaborator", role="org_member"):
    return client.post(
        "/api/settings/organization/members",
        headers=headers,
        json={"display_name": display_name, "email": email, "role": role},
    )


def test_organization_admin_provisions_member_who_can_sign_in(client, user_factory):
    organization = user_factory(display_name="Studio Owner", account_type="organization", organization_name="Studio Provision")
    response = add_member(client, organization["headers"], "new.member@authentiq.dev", display_name="New Member")
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["member"]["email"] == "new.member@authentiq.dev"
    assert data["member"]["role"] == "org_member"
    assert data["member"]["status"] == "active"
    credentials = data["credentials"]
    assert credentials["one_time"] is True
    assert len(credentials["password"]) >= 16

    session = login_user(client, credentials["email"], credentials["password"])
    assert session["user"]["organization_id"] == organization["user"]["organization_id"]
    assert session["user"]["role"] == "creator"
    assert session["user"]["account_type"] == "organization"

    organization_view = client.get("/api/settings/organization", headers=session["headers"])
    assert organization_view.status_code == 200
    payload = organization_view.json()
    assert payload["can_manage"] is False
    assert {member["email"] for member in payload["members"]} == {"new.member@authentiq.dev", organization["email"]}


def test_organization_admin_can_appoint_second_admin(client, user_factory):
    organization = user_factory(account_type="organization", organization_name="Second Admin Studio")
    response = add_member(client, organization["headers"], "second.admin@authentiq.dev", role="org_admin")
    assert response.status_code == 201, response.text
    session = login_user(client, "second.admin@authentiq.dev", response.json()["credentials"]["password"])
    assert session["user"]["role"] == "org_admin"
    follow_up = add_member(client, session["headers"], "third.member@authentiq.dev")
    assert follow_up.status_code == 201, follow_up.text


def test_individual_creator_cannot_provision_members(client, user_factory):
    creator = user_factory()
    response = add_member(client, creator["headers"], "blocked@authentiq.dev")
    assert response.status_code == 404
    assert "organization" in response.json()["detail"].lower()


def test_new_member_cannot_provision_other_members(client, user_factory):
    organization = user_factory(account_type="organization", organization_name="Permission Studio")
    created = add_member(client, organization["headers"], "limited.member@authentiq.dev")
    session = login_user(client, created.json()["credentials"]["email"], created.json()["credentials"]["password"])
    response = add_member(client, session["headers"], "should.fail@authentiq.dev")
    assert response.status_code == 403


def test_duplicate_email_is_rejected(client, user_factory):
    organization = user_factory(account_type="organization", organization_name="Duplicate Studio")
    first = add_member(client, organization["headers"], "duplicate.member@authentiq.dev")
    assert first.status_code == 201
    second = add_member(client, organization["headers"], "DUPLICATE.MEMBER@authentiq.dev")
    assert second.status_code == 409


def test_admin_can_rotate_member_password_and_revoke_sessions(client, user_factory):
    organization = user_factory(account_type="organization", organization_name="Rotation Studio")
    created = add_member(client, organization["headers"], "rotate.member@authentiq.dev").json()
    session = login_user(client, created["credentials"]["email"], created["credentials"]["password"])

    rotated = client.post(
        f"/api/settings/organization/members/{created['member']['user_id']}/password",
        headers=organization["headers"],
    )
    assert rotated.status_code == 200, rotated.text
    new_password = rotated.json()["credentials"]["password"]
    assert new_password != created["credentials"]["password"]

    stale = client.post(
        "/api/auth/login",
        json={"email": created["credentials"]["email"], "password": created["credentials"]["password"]},
    )
    assert stale.status_code == 401

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 401

    fresh_session = login_user(client, created["credentials"]["email"], new_password)
    assert fresh_session["user"]["email"] == created["credentials"]["email"]


def test_member_password_reset_requires_management_rights(client, user_factory):
    organization = user_factory(account_type="organization", organization_name="Ownership Guard Studio")
    created = add_member(client, organization["headers"], "guarded.member@authentiq.dev").json()
    member_session = login_user(client, created["credentials"]["email"], created["credentials"]["password"])
    response = client.post(
        f"/api/settings/organization/members/{created['member']['user_id']}/password",
        headers=member_session["headers"],
    )
    assert response.status_code == 403
