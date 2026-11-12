import hashlib


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return ""
    layer = [bytes.fromhex(value) for value in hashes]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [hashlib.sha256(layer[i] + layer[i + 1]).digest() for i in range(0, len(layer), 2)]
    return layer[0].hex()


def chunk_digest(index: int, data: bytes) -> str:
    return hashlib.sha256(str(index).encode() + b":" + data).hexdigest()
