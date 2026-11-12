import argparse
import json
from pathlib import Path

FIELD_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fingerprint", help="64-character SHA-256 fingerprint in hex")
    parser.add_argument("secret", help="Commitment secret in hex or decimal")
    parser.add_argument("--output", default="build/input.json")
    args = parser.parse_args()

    fingerprint = args.fingerprint.removeprefix("0x")
    if len(fingerprint) != 64:
        raise SystemExit("fingerprint must be a 32-byte SHA-256 hex digest")
    secret = int(args.secret, 16) if args.secret.lower().startswith("0x") else int(args.secret)
    payload = {
        "fingerprint": str(int(fingerprint, 16) % FIELD_PRIME),
        "secret": str(secret % FIELD_PRIME),
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(destination), **payload}, indent=2))


if __name__ == "__main__":
    main()
