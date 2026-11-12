import hashlib
import math

from app.fingerprint.chunking import chunk_digest, merkle_root
from app.fingerprint.sha256 import sha256_bytes, sha256_file, sha256_file_chunked
from tests.helpers import auth_headers, register_user, upload_file


def test_sha256_helpers_match_hashlib(tmp_path):
    content = bytes(range(256)) * 400
    path = tmp_path / "sample.bin"
    path.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    assert sha256_bytes(content) == expected
    assert sha256_file(path) == expected

    chunked = sha256_file_chunked(path, chunk_size=4096)
    assert chunked["sha256"] == expected
    assert chunked["size"] == len(content)
    assert len(chunked["chunks"]) == math.ceil(len(content) / 4096)
    assert b"".join(
        path.read_bytes()[index * 4096 : (index + 1) * 4096] for index in range(len(chunked["chunks"]))
    ) == content
    assert all(len(chunk["sha256"]) == 64 for chunk in chunked["chunks"])


def test_merkle_root_and_chunk_digest_are_deterministic():
    digests = [hashlib.sha256(str(index).encode()).hexdigest() for index in range(5)]
    assert merkle_root([]) == ""
    assert merkle_root(digests) == merkle_root(digests)
    assert merkle_root(digests) != merkle_root(digests[:-1])
    assert chunk_digest(0, b"data") != chunk_digest(1, b"data")
    assert chunk_digest(0, b"data") == chunk_digest(0, b"data")


def test_chunked_upload_produces_verified_overall_fingerprint(client, user_factory):
    user = user_factory()
    content = b"AUTHENTIQ chunked upload test." * 5000
    upload = upload_file(client, user["headers"], content, filename="chunks.txt")

    assert upload["status"] == "completed"
    assert upload["uploaded_chunks"] == upload["total_chunks"]
    assert upload["final_sha256"] == hashlib.sha256(content).hexdigest()

    status = client.get(f"/api/uploads/{upload['upload_id']}", headers=user["headers"])
    assert status.status_code == 200
    assert status.json()["final_sha256"] == upload["final_sha256"]


def test_chunk_checksum_mismatch_is_rejected(client, user_factory):
    user = user_factory()
    content = b"checksum check"
    initiate = client.post(
        "/api/uploads/initiate",
        headers=user["headers"],
        json={
            "filename": "checksum.txt",
            "size_bytes": len(content),
            "mime_type": "text/plain",
            "total_chunks": 1,
            "chunk_size": 1024,
        },
    )
    upload_id = initiate.json()["upload_id"]
    response = client.post(
        f"/api/uploads/{upload_id}/chunk",
        headers=user["headers"],
        data={"chunk_index": "0", "sha256": "0" * 64},
        files={"file": ("checksum.txt", content, "text/plain")},
    )
    assert response.status_code == 422


def test_incomplete_upload_cannot_complete(client, user_factory):
    user = user_factory()
    content = b"x" * 4096
    initiate = client.post(
        "/api/uploads/initiate",
        headers=user["headers"],
        json={
            "filename": "incomplete.txt",
            "size_bytes": len(content),
            "mime_type": "text/plain",
            "total_chunks": 4,
            "chunk_size": 1024,
        },
    )
    assert initiate.status_code == 200
    upload_id = initiate.json()["upload_id"]
    chunk = content[:1024]
    assert client.post(
        f"/api/uploads/{upload_id}/chunk",
        headers=user["headers"],
        data={"chunk_index": "0", "sha256": hashlib.sha256(chunk).hexdigest()},
        files={"file": ("incomplete.txt", chunk, "text/plain")},
    ).status_code == 200

    complete = client.post(f"/api/uploads/{upload_id}/complete", headers=user["headers"])
    assert complete.status_code == 400
    assert "missing" in complete.json()["detail"].lower()


def test_client_sha256_mismatch_is_rejected(client, user_factory):
    user = user_factory()
    content = b"client hash mismatch"
    initiate = client.post(
        "/api/uploads/initiate",
        headers=user["headers"],
        json={
            "filename": "mismatch.txt",
            "size_bytes": len(content),
            "mime_type": "text/plain",
            "total_chunks": 1,
            "chunk_size": len(content),
        },
    )
    upload_id = initiate.json()["upload_id"]
    client.post(
        f"/api/uploads/{upload_id}/chunk",
        headers=user["headers"],
        data={"chunk_index": "0", "sha256": hashlib.sha256(content).hexdigest()},
        files={"file": ("mismatch.txt", content, "text/plain")},
    )
    complete = client.post(
        f"/api/uploads/{upload_id}/complete",
        headers=user["headers"],
        data={"client_sha256": "f" * 64},
    )
    assert complete.status_code == 422


def test_upload_validation_and_ownership(client, user_factory):
    owner = user_factory()
    stranger = register_user(client)

    blocked = client.post(
        "/api/uploads/initiate",
        headers=owner["headers"],
        json={
            "filename": "payload.exe",
            "size_bytes": 10,
            "mime_type": "application/octet-stream",
            "total_chunks": 1,
            "chunk_size": 10,
        },
    )
    assert blocked.status_code == 415

    wrong_chunks = client.post(
        "/api/uploads/initiate",
        headers=owner["headers"],
        json={
            "filename": "wrong.txt",
            "size_bytes": 100,
            "mime_type": "text/plain",
            "total_chunks": 1,
            "chunk_size": 60,
        },
    )
    assert wrong_chunks.status_code == 400

    upload = upload_file(client, owner["headers"], b"ownership check", filename="owned.txt")
    assert client.get(f"/api/uploads/{upload['upload_id']}", headers=stranger["headers"]).status_code == 404
    assert client.get(f"/api/uploads/{upload['upload_id']}", headers=auth_headers("bad-token")).status_code == 401
