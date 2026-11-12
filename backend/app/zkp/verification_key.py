"""Private verification credentials for anonymous ownership proofs.

The key is the opening of the registered Pedersen commitment:

    key = "aqv1_<s>_<blinding>"     (s = Poseidon(sha256, secret))

It is derived at registration time, can be re-issued to the signed-in owner,
and is only ever used inside the browser to build a Schnorr proof. The public
SHA-256 fingerprint is never a valid private credential.
"""

import re

from app.services.access import secret_for
from app.zkp.field import commitment_for

KEY_PREFIX = "aqv1"
_KEY_PATTERN = re.compile(r"^aqv1_([0-9a-f]{64})_([0-9a-f]{64})$", re.IGNORECASE)


def verification_key_for(registration) -> str:
    secret_int, blinding_int = secret_for(registration)
    opening = commitment_for(registration.sha256, secret_int)
    return f"{KEY_PREFIX}_{opening:064x}_{blinding_int:064x}"


def parse_verification_key(value: str) -> tuple[int, int] | None:
    match = _KEY_PATTERN.match((value or "").strip().lower())
    if not match:
        return None
    return int(match.group(1), 16), int(match.group(2), 16)
