import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sha256_file_chunked(path: Path, chunk_size: int = 1024 * 1024) -> dict:
    hasher = hashlib.sha256()
    chunks = []
    total = 0
    with path.open("rb") as handle:
        index = 0
        while True:
            data = handle.read(chunk_size)
            if not data:
                break
            hasher.update(data)
            chunks.append({"index": index, "size": len(data), "sha256": sha256_bytes(data)})
            total += len(data)
            index += 1
    return {"sha256": hasher.hexdigest(), "size": total, "chunks": chunks}
