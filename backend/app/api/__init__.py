from fastapi import APIRouter

from app.api import (
    admin,
    auth,
    dashboard,
    fingerprints,
    public_records,
    public_verification,
    registrations,
    uploads,
    zkp,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(registrations.router)
api_router.include_router(fingerprints.router)
api_router.include_router(uploads.router)
api_router.include_router(zkp.router)
api_router.include_router(admin.router)
api_router.include_router(public_verification.router)
api_router.include_router(public_verification.public_fingerprints)
api_router.include_router(public_records.router)

