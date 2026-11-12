import secrets

from app.core.database import SessionLocal
from app.models import Registration
from app.security.crypto import utcnow
from app.services.access import secret_for
from app.zkp.field import FIELD_PRIME
from app.zkp.sigma import generate_proof
from tests.helpers import create_registration


def _server_proof(registration_id: str, nonce: str, random_opening: bool = False) -> dict:
    with SessionLocal() as db:
        registration = db.get(Registration, registration_id)
        if random_opening:
            secret_int = secrets.randbelow(FIELD_PRIME - 1) + 1
            blinding_int = secrets.randbelow(FIELD_PRIME - 1) + 1
        else:
            secret_int, blinding_int = secret_for(registration)
        return generate_proof(
            registration.sha256,
            registration.registration_id,
            nonce,
            registration.commitment,
            secret_int,
            blinding_int,
        )


def _challenge(client, registration, file_sha256=None):
    return client.post(
        "/api/public/verify/anonymous/challenge",
        json={
            "registration_id": registration["registration_id"],
            "file_sha256": file_sha256 or registration["sha256"],
        },
    )


def test_private_key_is_issued_at_registration_and_revealable(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"])

    key = created["verification_key"]
    assert key.startswith("aqv1_")
    parts = key.split("_")
    assert len(parts) == 3 and len(parts[1]) == 64 and len(parts[2]) == 64
    assert created["registration"]["sha256"] not in key

    revealed = client.get(
        f"/api/registrations/{created['registration']['id']}/verification-key",
        headers=user["headers"],
    )
    assert revealed.status_code == 200
    assert revealed.json()["verification_key"] == key

    anonymous = client.get(f"/api/registrations/{created['registration']['id']}/verification-key")
    assert anonymous.status_code == 401

    detail = client.get(f"/api/registrations/{created['registration']['id']}", headers=user["headers"])
    assert "verification_key" not in detail.json()


def test_anonymous_verification_without_login(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"anonymous ownership subject")
    registration = created["registration"]

    challenge_response = _challenge(client, registration)
    assert challenge_response.status_code == 200, challenge_response.text
    challenge = challenge_response.json()
    assert challenge["registration_id"] == registration["registration_id"]
    assert challenge["fingerprint"] == registration["sha256"]
    assert "verification_key" not in challenge
    assert challenge["proof_system"] == "AUTHENTIQ-SCHNORR-BN254-G1-V1"

    proof = _server_proof(registration["id"], challenge["nonce"])
    verified = client.post(
        "/api/public/verify/anonymous/verify",
        json={"challenge_id": challenge["challenge_id"], "proof": proof},
    )
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["valid"] is True
    assert body["checks"] == {
        "registration_exists": True,
        "file_fingerprint_matches": True,
        "challenge_valid": True,
        "proof_valid": True,
        "private_key_disclosed": False,
        "login_required": False,
    }
    assert body["public_record"]["fingerprint"] == registration["sha256"]

    replay = client.post(
        "/api/public/verify/anonymous/verify",
        json={"challenge_id": challenge["challenge_id"], "proof": proof},
    )
    assert replay.status_code == 409


def test_anonymous_verification_rejects_wrong_file_and_unknown_record(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"])
    registration = created["registration"]

    wrong_file = _challenge(client, registration, file_sha256="a" * 64)
    assert wrong_file.status_code == 422
    assert "fingerprint" in wrong_file.json()["detail"].lower()

    unknown = _challenge(client, {"registration_id": "AQ-2026-DOESNOTEX", "sha256": "b" * 64})
    assert unknown.status_code == 404


def test_proof_with_wrong_private_key_is_rejected(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"])
    registration = created["registration"]
    challenge = _challenge(client, registration).json()

    wrong_key_proof = _server_proof(registration["id"], challenge["nonce"], random_opening=True)
    response = client.post(
        "/api/public/verify/anonymous/verify",
        json={"challenge_id": challenge["challenge_id"], "proof": wrong_key_proof},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["checks"]["proof_valid"] is False
    assert response.json()["checks"]["private_key_disclosed"] is False


def test_tampered_anonymous_proof_is_rejected(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"])
    registration = created["registration"]
    challenge = _challenge(client, registration).json()
    proof = _server_proof(registration["id"], challenge["nonce"])

    tampered = {**proof, "response": ["1" * 64, "2" * 64]}
    response = client.post(
        "/api/public/verify/anonymous/verify",
        json={"challenge_id": challenge["challenge_id"], "proof": tampered},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["checks"]["proof_valid"] is False


def test_expired_anonymous_challenge_is_rejected(client, user_factory):
    from datetime import timedelta

    from app.models import ZkpChallenge

    user = user_factory()
    created = create_registration(client, user["headers"])
    registration = created["registration"]
    challenge = _challenge(client, registration).json()

    with SessionLocal() as db:
        record = db.get(ZkpChallenge, challenge["challenge_id"])
        record.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    proof = _server_proof(registration["id"], challenge["nonce"])
    response = client.post(
        "/api/public/verify/anonymous/verify",
        json={"challenge_id": challenge["challenge_id"], "proof": proof},
    )
    assert response.status_code == 410


def test_public_fingerprint_existence_check(client, user_factory):
    user = user_factory()
    created = create_registration(client, user["headers"], content=b"public fingerprint subject")
    registration = created["registration"]

    found = client.post("/api/public/fingerprints/check", json={"sha256": registration["sha256"]})
    assert found.status_code == 200
    assert found.json()["registered"] is True
    assert found.json()["records"] >= 1
    assert "registration_id" not in found.json()

    missing = client.post("/api/public/fingerprints/check", json={"sha256": "c" * 64})
    assert missing.status_code == 200
    assert missing.json()["registered"] is False
    assert missing.json()["records"] == 0
