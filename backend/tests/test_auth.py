from tests.helpers import PASSWORD, auth_headers, login_user, register_user


def test_register_login_refresh_and_me(client):
    user = register_user(client, display_name="Ada Creator")
    assert user["user"]["email"] == user["email"]
    assert user["user"]["role"] == "creator"

    me = client.get("/api/auth/me", headers=user["headers"])
    assert me.status_code == 200
    assert me.json()["email"] == user["email"]

    bad_login = client.post("/api/auth/login", json={"email": user["email"], "password": "Wrong!Password1"})
    assert bad_login.status_code == 401

    logged_in = login_user(client, user["email"])
    assert logged_in["user"]["id"] == user["user"]["id"]

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": logged_in["refresh_token"]})
    assert refreshed.status_code == 200
    rotated = refreshed.json()
    assert rotated["refresh_token"] != logged_in["refresh_token"]

    stale = client.post("/api/auth/refresh", json={"refresh_token": logged_in["refresh_token"]})
    assert stale.status_code == 401


def test_duplicate_account_and_weak_password_rejected(client):
    user = register_user(client)
    duplicate = client.post(
        "/api/auth/register",
        json={
            "display_name": "Duplicate",
            "email": user["email"],
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "account_type": "individual",
            "accept_terms": True,
        },
    )
    assert duplicate.status_code == 409

    weak = client.post(
        "/api/auth/register",
        json={
            "display_name": "Weak",
            "email": "weak-password@authentiq.dev",
            "password": "short",
            "confirm_password": "short",
            "account_type": "individual",
            "accept_terms": True,
        },
    )
    assert weak.status_code == 422

    mismatch = client.post(
        "/api/auth/register",
        json={
            "display_name": "Mismatch",
            "email": "mismatch-password@authentiq.dev",
            "password": PASSWORD,
            "confirm_password": PASSWORD + "x",
            "account_type": "individual",
            "accept_terms": True,
        },
    )
    assert mismatch.status_code == 422


def test_organization_registration_creates_admin_role(client):
    organization = register_user(
        client,
        display_name="Org Owner",
        account_type="organization",
        organization_name="Studio Nine",
    )
    assert organization["user"]["role"] == "org_admin"
    assert organization["user"]["organization_id"]
    assert organization["user"]["organization_name"] == "Studio Nine"


def test_change_password_revokes_sessions(client):
    user = register_user(client)
    session_list = client.get("/api/auth/sessions", headers=user["headers"])
    assert session_list.status_code == 200
    assert len(session_list.json()) == 1

    change = client.post(
        "/api/auth/change-password",
        headers=user["headers"],
        json={
            "current_password": PASSWORD,
            "new_password": "Authentiq!Changed2026",
            "confirm_password": "Authentiq!Changed2026",
        },
    )
    assert change.status_code == 200

    revoked = client.get("/api/auth/me", headers=user["headers"])
    assert revoked.status_code == 401

    relogin = login_user(client, user["email"], "Authentiq!Changed2026")
    assert relogin["user"]["id"] == user["user"]["id"]


def test_logout_revokes_current_session(client):
    user = register_user(client)
    logout = client.post(
        "/api/auth/logout",
        headers=user["headers"],
        json={"refresh_token": user["refresh_token"]},
    )
    assert logout.status_code == 200
    assert client.get("/api/auth/me", headers=user["headers"]).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": user["refresh_token"]}).status_code == 401


def test_password_reset_flow_is_single_use(client):
    user = register_user(client)
    forgot = client.post("/api/auth/forgot-password", json={"email": user["email"]})
    assert forgot.status_code == 200
    token = forgot.json()["detail"]
    assert token

    reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "new_password": "Authentiq!Reset2026",
            "confirm_password": "Authentiq!Reset2026",
        },
    )
    assert reset.status_code == 200
    assert client.get("/api/auth/me", headers=user["headers"]).status_code == 401
    login_user(client, user["email"], "Authentiq!Reset2026")

    reused = client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "new_password": "Authentiq!Reset2027",
            "confirm_password": "Authentiq!Reset2027",
        },
    )
    assert reused.status_code == 400


def test_unauthenticated_requests_are_rejected(client):
    for path in ["/api/auth/me", "/api/registrations", "/api/dashboard/summary", "/api/teams", "/api/ledger/status"]:
        assert client.get(path).status_code == 401
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health").json()["ledger"]["mode"] == "simulation"
    assert client.get("/api/auth/me", headers=auth_headers("not-a-jwt")).status_code == 401
