import hashlib

from app.zkp.poseidon import FIELD_PRIME, poseidon2

SCHEME = "AUTHENTIQ-POSEIDON254-COMMITMENT-V1"


def compact_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def to_field_int(value: str | int | bytes) -> int:
    if isinstance(value, int):
        return value % FIELD_PRIME
    if isinstance(value, bytes):
        raw = value
    else:
        text = value.strip()
        try:
            raw = bytes.fromhex(text)
        except ValueError:
            raw = text.encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest(), "big") % FIELD_PRIME


def poseidon_hash(left: int, right: int) -> int:
    return poseidon2(left % FIELD_PRIME, right % FIELD_PRIME)


def fingerprint_field(fingerprint_hex: str) -> int:
    return int(fingerprint_hex, 16) % FIELD_PRIME


def commitment_for(fingerprint_hex: str, secret_int: int) -> int:
    return poseidon_hash(fingerprint_field(fingerprint_hex), secret_int)


def commitment_hex(value: int) -> str:
    return "0x" + format(value % FIELD_PRIME, "064x")


def int_hex(value: int) -> str:
    return "0x" + format(value % FIELD_PRIME, "064x")


def challenge_int(*parts: str) -> int:
    payload = "|".join(parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big") % FIELD_PRIME


def derive_generator(label: str) -> int:
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    value = int.from_bytes(digest, "big") % FIELD_PRIME
    return value or 1
