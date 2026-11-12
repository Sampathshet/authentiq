import math
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.fingerprint.chunking import merkle_root
from app.models import Upload, User
from app.schemas.content import UploadInitiateRequest, UploadOut
from app.security.crypto import sha256_hex
from app.services.audit import append_audit
from app.storage.files import encrypt_file_to, sha256_file
from app.storage.scanner import scan_path
from app.models import FileChunk

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _upload_dir(upload_id: str) -> Path:
    path = settings.upload_dir / "chunks" / upload_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _upload_out(upload: Upload) -> UploadOut:
    return UploadOut(
        upload_id=upload.id,
        filename=upload.filename,
        size_bytes=upload.size_bytes,
        total_chunks=upload.total_chunks,
        chunk_size=upload.chunk_size,
        uploaded_chunks=upload.uploaded_chunks,
        status=upload.status,
        final_sha256=upload.final_sha256,
    )


@router.post("/initiate", response_model=UploadOut)
def initiate_upload(
    payload: UploadInitiateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.size_bytes > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_file_size_mb} MB limit",
        )
    if payload.chunk_size > settings.max_chunk_size_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chunk size exceeds the configured limit")
    expected_chunks = math.ceil(payload.size_bytes / payload.chunk_size)
    if payload.total_chunks != expected_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"total_chunks must be {expected_chunks} for the supplied size and chunk size",
        )
    suffix = Path(payload.filename).suffix.lower()
    if suffix and suffix not in settings.allowed_extension_list:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"File type {suffix} is not allowed")
    upload = Upload(
        user_id=user.id,
        filename=payload.filename,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        total_chunks=payload.total_chunks,
        chunk_size=payload.chunk_size,
        status="initiated",
    )
    db.add(upload)
    db.flush()
    _upload_dir(upload.id)
    append_audit(
        db,
        "upload_initiated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="upload",
        entity_id=upload.id,
        metadata={"filename": payload.filename, "size": payload.size_bytes, "chunks": payload.total_chunks},
    )
    db.commit()
    return _upload_out(upload)


@router.post("/{upload_id}/chunk", response_model=UploadOut)
def upload_chunk(
    upload_id: str,
    chunk_index: int = Form(...),
    sha256: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    upload = db.get(Upload, upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    if upload.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Upload is already completed")
    if chunk_index < 0 or chunk_index >= upload.total_chunks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chunk index is out of range")
    data = file.file.read(upload.chunk_size + 1)
    if len(data) > upload.chunk_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Chunk exceeds the declared chunk size")
    if chunk_index < upload.total_chunks - 1 and len(data) != upload.chunk_size:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Non-final chunks must match the declared chunk size")
    actual = sha256_hex(data)
    if actual.lower() != sha256.lower():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Chunk checksum mismatch")
    folder = _upload_dir(upload.id)
    chunk_path = folder / f"{chunk_index:06d}.chunk"
    existing = db.execute(
        select(FileChunk).where(FileChunk.upload_id == upload.id, FileChunk.chunk_index == chunk_index)
    ).scalar_one_or_none()
    if existing:
        if existing.sha256 == actual:
            return _upload_out(upload)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A different chunk already exists at this index")
    chunk_path.write_bytes(data)
    db.add(
        FileChunk(
            upload_id=upload.id,
            chunk_index=chunk_index,
            sha256=actual,
            size_bytes=len(data),
            storage_path=str(chunk_path),
        )
    )
    upload.uploaded_chunks += 1
    upload.status = "uploading"
    db.flush()
    db.commit()
    return _upload_out(upload)


@router.post("/{upload_id}/complete", response_model=UploadOut)
def complete_upload(
    upload_id: str,
    client_sha256: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    upload = db.get(Upload, upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    if upload.status == "completed":
        return _upload_out(upload)
    chunks = db.execute(
        select(FileChunk).where(FileChunk.upload_id == upload.id).order_by(FileChunk.chunk_index.asc())
    ).scalars().all()
    if len(chunks) != upload.total_chunks:
        missing = sorted(set(range(upload.total_chunks)) - {chunk.chunk_index for chunk in chunks})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is missing {len(missing)} chunk(s): {missing[:20]}",
        )
    for expected_index, chunk in enumerate(chunks):
        if chunk.chunk_index != expected_index:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chunk ordering is invalid")
        if not Path(chunk.storage_path).exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Chunk {expected_index} is missing from storage")
        if sha256_file(Path(chunk.storage_path)) != chunk.sha256:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Chunk {expected_index} is corrupted")
    folder = _upload_dir(upload.id)
    assembled = folder / "assembled.bin"
    with assembled.open("wb") as writer:
        for chunk in chunks:
            writer.write(Path(chunk.storage_path).read_bytes())
    if assembled.stat().st_size != upload.size_bytes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assembled file size does not match the declared size")
    final_hash = sha256_file(assembled)
    if client_sha256 and client_sha256.lower() != final_hash:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Overall SHA-256 does not match the client fingerprint",
        )
    scan = scan_path(upload.filename, assembled, settings.allowed_extension_list)
    if not scan["clean"]:
        append_audit(
            db,
            "upload_blocked",
            actor_id=user.id,
            actor_ref=user.email,
            entity_type="upload",
            entity_id=upload.id,
            metadata={"threats": scan["threats"]},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": "File rejected by security scanner", "threats": scan["threats"]})
    destination = settings.upload_dir / user.id / f"{upload.id}.aqenc"
    encrypted_size = encrypt_file_to(assembled, destination)
    upload.final_sha256 = final_hash
    upload.storage_path = str(destination)
    upload.per_chunk_sha256 = [chunk.sha256 for chunk in chunks]
    upload.status = "completed"
    upload.uploaded_chunks = upload.total_chunks
    for chunk in chunks:
        chunk.storage_path = ""
    assembled.unlink(missing_ok=True)
    shutil.rmtree(folder, ignore_errors=True)
    append_audit(
        db,
        "fingerprint_generated",
        actor_id=user.id,
        actor_ref=user.email,
        entity_type="upload",
        entity_id=upload.id,
        metadata={
            "sha256": final_hash,
            "chunks": upload.total_chunks,
            "merkle_root": merkle_root([chunk.sha256 for chunk in chunks]),
            "scanner": scan["engine"],
        },
    )
    db.commit()
    return _upload_out(upload)


@router.get("/{upload_id}", response_model=UploadOut)
def get_upload(upload_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    upload = db.get(Upload, upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    return _upload_out(upload)
