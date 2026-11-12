from datetime import timedelta

from app.core.database import SessionLocal
from app.models import ZkpChallenge
from app.security.crypto import utcnow
from tests.helpers import create_registration


def _challenge(client, headers, registration):
    response = client.post(
        "/api/zkp/challenge",
        headers=headers,
        json={"registration_id": registration["registration_id"], "purpose": "proof"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_valid_proof_generation_and_verification(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"zero knowledge subject")
    registration = created["registration"]
    challenge = _challenge(client, user["headers"], registration)

    assert challenge["proof_system"] == "AUTHENTIQ-SCHNORR-BN254-G1-V1"
    assert "does not verify the file hash inside the proof" in challenge["statement"]
    assert challenge["is_groth16"] is False
    assert challenge["poseidon_commitment"] == registration["poseidon_commitment"]

    generated = client.post(
        "/api/zkp/generate",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "challenge_id": challenge["challenge_id"],
            "file_sha256": registration["sha256"],
        },
    )
    assert generated.status_code == 200, generated.text
    proof = generated.json()["proof"]
    assert proof["scheme"] == "AUTHENTIQ-SCHNORR-BN254-G1-V1"
    assert len(proof["response"]) == 2

    verified = client.post(
        "/api/zkp/verify",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "nonce": challenge["nonce"],
            "proof": proof,
            "public_signals": proof["public_signals"],
        },
    )
    assert verified.status_code == 200
    assert verified.json()["valid"] is True
    assert "opening of the registered ownership commitment" in verified.json()["statement"]

    replay = client.post(
        "/api/zkp/verify",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "nonce": challenge["nonce"],
            "proof": proof,
            "public_signals": proof["public_signals"],
        },
    )
    assert replay.status_code == 409

    proofs = client.get(f"/api/zkp/proofs/{registration['registration_id']}", headers=user["headers"])
    assert proofs.status_code == 200
    assert any(item["status"] == "verified" for item in proofs.json()["items"])


def test_proof_rejects_wrong_file_hash(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"])
    registration = created["registration"]
    challenge = _challenge(client, user["headers"], registration)

    response = client.post(
        "/api/zkp/generate",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "challenge_id": challenge["challenge_id"],
            "file_sha256": "a" * 64,
        },
    )
    assert response.status_code == 422
    assert "does not match" in response.json()["detail"].lower()


def test_tampered_proof_and_public_signals_are_invalid(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"tamper detection")
    registration = created["registration"]

    challenge = _challenge(client, user["headers"], registration)
    generated = client.post(
        "/api/zkp/generate",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "challenge_id": challenge["challenge_id"],
            "file_sha256": registration["sha256"],
        },
    ).json()
    proof = generated["proof"]
    tampered = {**proof, "response": ["1" * 64, "2" * 64]}
    tampered_result = client.post(
        "/api/zkp/verify",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "nonce": challenge["nonce"],
            "proof": tampered,
            "public_signals": proof["public_signals"],
        },
    )
    assert tampered_result.status_code == 200
    assert tampered_result.json()["valid"] is False
    assert "verification failed" in tampered_result.json()["message"].lower()

    challenge = _challenge(client, user["headers"], registration)
    generated = client.post(
        "/api/zkp/generate",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "challenge_id": challenge["challenge_id"],
            "file_sha256": registration["sha256"],
        },
    ).json()
    mismatched_signals = {**generated["proof"]["public_signals"], "registration_id": "AQ-FAKE-0000"}
    signals_result = client.post(
        "/api/zkp/verify",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "nonce": challenge["nonce"],
            "proof": generated["proof"],
            "public_signals": mismatched_signals,
        },
    )
    assert signals_result.status_code == 200
    assert signals_result.json()["valid"] is False
    assert "public signals" in signals_result.json()["message"].lower()


def test_expired_challenge_cannot_generate_proof(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"])
    registration = created["registration"]
    challenge = _challenge(client, user["headers"], registration)

    with SessionLocal() as db:
        record = db.get(ZkpChallenge, challenge["challenge_id"])
        record.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    response = client.post(
        "/api/zkp/generate",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "challenge_id": challenge["challenge_id"],
            "file_sha256": registration["sha256"],
        },
    )
    assert response.status_code == 410


def test_public_silent_share_verification_and_usage_limit(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"public share subject")
    registration = created["registration"]

    share = client.post(
        "/api/sharing/create",
        headers=user["headers"],
        json={
            "registration_id": registration["registration_id"],
            "expires_in_hours": 24,
            "max_uses": 1,
            "message": "Verify my ownership proof",
            "disclosure": {"show_fingerprint": True, "anonymous": True},
        },
    )
    assert share.status_code == 201, share.text
    package = share.json()["proof_package"]
    verification_id = share.json()["verification_id"]
    assert share.json()["verification_url"].endswith(verification_id)

    public_record = client.get(f"/api/public/verify/{verification_id}")
    assert public_record.status_code == 200
    assert public_record.json()["requires_proof"] is True
    assert public_record.json()["public_record"]["fingerprint"] == registration["sha256"]

    verified = client.post(f"/api/public/verify/{verification_id}", json={"proof_package": package})
    assert verified.status_code == 200, verified.text
    assert verified.json()["valid"] is True
    assert verified.json()["uses"] == 1

    exhausted = client.post(f"/api/public/verify/{verification_id}", json={"proof_package": package})
    assert exhausted.status_code == 409

    status = client.get(f"/api/public/verify/{verification_id}")
    assert status.json()["status"] == "verified"
