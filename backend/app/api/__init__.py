from fastapi import APIRouter

from app.api import (
    auth,
    dashboard,
    fingerprints,
    registrations,
    uploads,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(registrations.router)
api_router.include_router(fingerprints.router)
api_router.include_router(uploads.router)

