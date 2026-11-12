from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.fingerprint.chunking import merkle_root
from app.fingerprint.sha256 import sha256_bytes
from app.models import Registration, User
from app.schemas.content import FingerprintVerifyRequest
from app.services.serializers import registration_out

router = APIRouter(prefix="/fingerprints", tags=["fingerprints"])


@router.post("/generate")
async def generate_fingerprint(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    data = await file.read(settings.max_file_size_bytes + 1)
    if len(data) > settings.max_file_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds the configured size limit")
    chunk_size = 1024 * 1024
    chunks = []
    for index in range(0, len(data), chunk_size):
        piece = data[index:index + chunk_size]
        chunks.append(sha256_bytes(piece))
    return {
        "filename": file.filename,
        "size_bytes": len(data),
        "sha256": sha256_bytes(data),
        "chunk_size": chunk_size,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "merkle_root": merkle_root(chunks),
        "canonical_definition": "SHA-256 over the complete original file bytes. Chunk hashes and the Merkle root are integrity diagnostics only.",
    }


@router.post("/verify")
async def verify_fingerprint(
    file: UploadFile = File(...),
    fingerprint: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await file.read(settings.max_file_size_bytes + 1)
    if len(data) > settings.max_file_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds the configured size limit")
    actual = sha256_bytes(data)
    matches = db.execute(select(Registration).where(Registration.sha256 == fingerprint.lower())).scalars().all()
    accessible = [
        match
        for match in matches
        if match.user_id == user.id
        or (user.organization_id and match.organization_id == user.organization_id)
        or match.privacy in {"public_fingerprint", "public"}
    ]
    return {
        "matches": actual == fingerprint.lower(),
        "computed_sha256": actual,
        "expected_sha256": fingerprint.lower(),
        "registrations": [
            registration_out(match)
            for match in accessible[:10]
        ],
        "total_matches": len(matches),
    }
