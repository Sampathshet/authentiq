import hashlib
import math
import secrets

PASSWORD = "Authentiq!Test2026"
CHUNK_SIZE = 64 * 1024


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, display_name="Test Creator", account_type="individual", organization_name=None, created=None):
    email = f"user-{secrets.token_hex(6)}@authentiq.dev"
    payload = {
        "display_name": display_name,
        "email": email,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        "account_type": account_type,
        "accept_terms": True,
    }
    if organization_name:
        payload["organization_name"] = organization_name
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    record = {
        "email": email,
        "password": PASSWORD,
        "token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
        "headers": auth_headers(data["access_token"]),
    }
    if created is not None:
        created.append(record)
    return record


def login_user(client, email, password=PASSWORD):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    data = response.json()
    return {
        "token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
        "headers": auth_headers(data["access_token"]),
    }


def upload_file(client, headers, content: bytes, filename="artifact.txt", mime_type="text/plain"):
    total_chunks = math.ceil(len(content) / CHUNK_SIZE) if content else 1
    initiate = client.post(
        "/api/uploads/initiate",
        headers=headers,
        json={
            "filename": filename,
            "size_bytes": len(content),
            "mime_type": mime_type,
            "total_chunks": total_chunks,
            "chunk_size": CHUNK_SIZE,
        },
    )
    assert initiate.status_code == 200, initiate.text
    upload = initiate.json()
    for index in range(total_chunks):
        chunk = content[index * CHUNK_SIZE : (index + 1) * CHUNK_SIZE]
        response = client.post(
            f"/api/uploads/{upload['upload_id']}/chunk",
            headers=headers,
            data={"chunk_index": str(index), "sha256": hashlib.sha256(chunk).hexdigest()},
            files={"file": (filename, chunk, mime_type)},
        )
        assert response.status_code == 200, response.text
    complete = client.post(
        f"/api/uploads/{upload['upload_id']}/complete",
        headers=headers,
        data={"client_sha256": hashlib.sha256(content).hexdigest()},
    )
    assert complete.status_code == 200, complete.text
    upload.update(complete.json())
    upload["content_sha256"] = hashlib.sha256(content).hexdigest()
    return upload


def create_registration(
    client,
    headers,
    content: bytes | None = None,
    filename="artifact.txt",
    title="Test Artifact",
    privacy="private",
    asset_type="document",
    team_id: str | None = None,
):
    content = content if content is not None else f"artifact-{secrets.token_hex(8)}".encode()
    upload = upload_file(client, headers, content, filename=filename)
    payload = {
        "upload_id": upload["upload_id"],
        "title": title,
        "description": "Integration test registration",
        "asset_type": asset_type,
        "privacy": privacy,
    }
    if team_id:
        payload["team_id"] = team_id
    response = client.post(
        "/api/registrations",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    data["upload"] = upload
    data["content"] = content
    return data
