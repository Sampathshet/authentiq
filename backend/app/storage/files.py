import hashlib
import os
import secrets
import struct
from collections.abc import Iterator
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

MAGIC = b"AQVL1"
PREFIX_SIZE = 8
CHUNK_SIZE = 1024 * 1024
TAG_SIZE = 16
MAX_CIPHERTEXT_CHUNK = CHUNK_SIZE + TAG_SIZE


def _vault_key() -> bytes:
    return hashlib.sha256((settings.secret_key + ":file-vault-v1").encode()).digest()


def _nonce(prefix: bytes, counter: int) -> bytes:
    return prefix + struct.pack(">I", counter)


def encrypt_file_to(source: Path, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    key = _vault_key()
    aes = AESGCM(key)
    prefix = secrets.token_bytes(PREFIX_SIZE)
    total = 0
    with source.open("rb") as reader, destination.open("wb") as writer:
        writer.write(MAGIC)
        writer.write(prefix)
        counter = 0
        while True:
            chunk = reader.read(CHUNK_SIZE)
            if not chunk:
                break
            ciphertext = aes.encrypt(_nonce(prefix, counter), chunk, str(counter).encode())
            writer.write(struct.pack(">I", len(ciphertext)))
            writer.write(ciphertext)
            total += len(ciphertext)
            counter += 1
        writer.write(struct.pack(">I", 0))
    return total


def decrypt_file_to(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    aes = AESGCM(_vault_key())
    with source.open("rb") as reader, destination.open("wb") as writer:
        magic = reader.read(len(MAGIC))
        if magic != MAGIC:
            raise ValueError("Not an AUTHENTIQ encrypted file")
        prefix = reader.read(PREFIX_SIZE)
        counter = 0
        while True:
            length_bytes = reader.read(4)
            if len(length_bytes) != 4:
                raise ValueError("Truncated encrypted file")
            length = struct.unpack(">I", length_bytes)[0]
            if length == 0:
                break
            if length > MAX_CIPHERTEXT_CHUNK:
                raise ValueError("Invalid encrypted chunk length")
            ciphertext = reader.read(length)
            if len(ciphertext) != length:
                raise ValueError("Truncated encrypted chunk")
            plaintext = aes.decrypt(_nonce(prefix, counter), ciphertext, str(counter).encode())
            writer.write(plaintext)
            counter += 1


def iter_decrypted(source: Path) -> Iterator[bytes]:
    aes = AESGCM(_vault_key())
    with source.open("rb") as reader:
        magic = reader.read(len(MAGIC))
        if magic != MAGIC:
            raise ValueError("Not an AUTHENTIQ encrypted file")
        prefix = reader.read(PREFIX_SIZE)
        counter = 0
        while True:
            length_bytes = reader.read(4)
            if len(length_bytes) != 4:
                raise ValueError("Truncated encrypted file")
            length = struct.unpack(">I", length_bytes)[0]
            if length == 0:
                break
            if length > MAX_CIPHERTEXT_CHUNK:
                raise ValueError("Invalid encrypted chunk length")
            ciphertext = reader.read(length)
            if len(ciphertext) != length:
                raise ValueError("Truncated encrypted chunk")
            yield aes.decrypt(_nonce(prefix, counter), ciphertext, str(counter).encode())
            counter += 1


def read_decrypted(source: Path) -> bytes:
    return b"".join(iter_decrypted(source))


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def stream_to_temp(source_path: Path, temp_path: Path) -> str:
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source_path, temp_path)
    return sha256_file(temp_path)
