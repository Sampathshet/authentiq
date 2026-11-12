import secrets

from app.zkp.curve import (
    GENERATOR,
    hash_to_curve,
    point_add,
    point_from_hex,
    point_to_hex,
    scalar_mul,
)
from app.zkp.field import (
    FIELD_PRIME,
    SCHEME,
    challenge_int,
    commitment_for,
    commitment_hex,
)

PEDERSEN_G = GENERATOR
PEDERSEN_H = hash_to_curve("AUTHENTIQ-PEDERSEN-H-V1")
SIGMA_SCHEME = "AUTHENTIQ-SCHNORR-BN254-G1-V1"
PUBLIC_SIGNAL_SCHEME = "AUTHENTIQ-PUBLIC-SIGNALS-V1"


def _commitment_point(fingerprint_hex: str, secret_int: int, blinding_int: int):
    s = commitment_for(fingerprint_hex, secret_int)
    return point_add(scalar_mul(s, PEDERSEN_G), scalar_mul(blinding_int, PEDERSEN_H))


def create_commitment(fingerprint_hex: str, secret_int: int | None = None) -> dict:
    secret = secret_int if secret_int is not None else secrets.randbelow(FIELD_PRIME - 1) + 1
    blinding = secrets.randbelow(FIELD_PRIME - 1) + 1
    poseidon_value = commitment_for(fingerprint_hex, secret)
    pedersen = _commitment_point(fingerprint_hex, secret, blinding)
    return {
        "secret_int": secret,
        "secret_hex": format(secret, "064x"),
        "blinding_int": blinding,
        "blinding_hex": format(blinding, "064x"),
        "poseidon_commitment": commitment_hex(poseidon_value),
        "poseidon_commitment_int": poseidon_value,
        "pedersen_commitment": point_to_hex(pedersen),
        "pedersen_commitment_int": int.from_bytes(bytes.fromhex(point_to_hex(pedersen)[2:]), "big"),
        "scheme": SCHEME,
        "proof_system": SIGMA_SCHEME,
    }


def public_signals(fingerprint_hex: str, registration_id: str, nonce: str, commitment: str) -> dict:
    return {
        "scheme": PUBLIC_SIGNAL_SCHEME,
        "fingerprint": fingerprint_hex,
        "registration_id": registration_id,
        "commitment": commitment,
        "challenge_nonce": nonce,
    }


def generate_proof(
    fingerprint_hex: str,
    registration_id: str,
    nonce: str,
    commitment_hex_value: str,
    secret_int: int,
    blinding_int: int,
) -> dict:
    commitment_point = point_from_hex(commitment_hex_value)
    s = commitment_for(fingerprint_hex, secret_int)
    u1 = secrets.randbelow(FIELD_PRIME - 1) + 1
    u2 = secrets.randbelow(FIELD_PRIME - 1) + 1
    anchor = point_add(scalar_mul(u1, PEDERSEN_G), scalar_mul(u2, PEDERSEN_H))
    challenge = challenge_int(
        SIGMA_SCHEME,
        point_to_hex(anchor),
        point_to_hex(commitment_point),
        fingerprint_hex.lower(),
        registration_id,
        nonce,
    )
    z1 = (u1 + challenge * s) % FIELD_PRIME
    z2 = (u2 + challenge * blinding_int) % FIELD_PRIME
    return {
        "scheme": SIGMA_SCHEME,
        "commitment": point_to_hex(commitment_point),
        "anchor": point_to_hex(anchor),
        "challenge": commitment_hex(challenge),
        "response": [format(z1, "064x"), format(z2, "064x")],
        "public_signals": public_signals(fingerprint_hex, registration_id, nonce, point_to_hex(commitment_point)),
    }


def verify_proof(proof: dict, fingerprint_hex: str, registration_id: str, nonce: str, commitment_hex_value: str) -> tuple[bool, str]:
    try:
        if proof.get("scheme") != SIGMA_SCHEME:
            return False, "Unsupported proof scheme"
        commitment = point_from_hex(commitment_hex_value)
        if point_from_hex(proof["commitment"]) != commitment:
            return False, "Proof commitment does not match the registered commitment"
        anchor = point_from_hex(proof["anchor"])
        stated_challenge = int(proof["challenge"], 16) % FIELD_PRIME
        z1 = int(proof["response"][0], 16) % FIELD_PRIME
        z2 = int(proof["response"][1], 16) % FIELD_PRIME
        expected = challenge_int(
            SIGMA_SCHEME,
            point_to_hex(anchor),
            point_to_hex(commitment),
            fingerprint_hex.lower(),
            registration_id,
            nonce,
        )
        if expected != stated_challenge:
            return False, "Fiat-Shamir challenge mismatch"
        left = point_add(scalar_mul(z1, PEDERSEN_G), scalar_mul(z2, PEDERSEN_H))
        right = point_add(anchor, scalar_mul(stated_challenge, commitment))
        if left != right:
            return False, "Schnorr equation verification failed"
        return True, "Proof is cryptographically valid"
    except (KeyError, IndexError, TypeError, ValueError):
        return False, "Malformed proof structure"


def verify_commitment(fingerprint_hex: str, secret_int: int, poseidon_commitment_hex: str) -> bool:
    try:
        return commitment_hex(commitment_for(fingerprint_hex, secret_int)).lower() == poseidon_commitment_hex.lower()
    except (TypeError, ValueError):
        return False


def recompute_commitment(fingerprint_hex: str, secret_int: int, blinding_int: int) -> str:
    return point_to_hex(_commitment_point(fingerprint_hex, secret_int, blinding_int))
