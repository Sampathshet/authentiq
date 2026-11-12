from fastapi import APIRouter

from app.api import (
    admin,
    alerts,
    auth,
    dashboard,
    fingerprints,
    ideas,
    provenance,
    public_records,
    public_verification,
    registrations,
    sharing,
    teams,
    transfers,
    uploads,
    versions,
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
api_router.include_router(sharing.router)
api_router.include_router(sharing.public_router)
api_router.include_router(ideas.router)
api_router.include_router(versions.router)
api_router.include_router(provenance.router)
api_router.include_router(teams.router)
api_router.include_router(alerts.router)
api_router.include_router(transfers.router)

