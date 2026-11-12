import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import settings
from app.core.database import init_db
from app.ledger import ledger_service
from app.zkp.sigma import SIGMA_SCHEME

logger = logging.getLogger("authentiq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    init_db()
    if settings.seed_demo:
        try:
            from app.seed import seed_demo_data

            seed_demo_data()
            logger.info("Demo workspace seeded")
        except Exception:
            logger.exception("Demo seed failed")
    if settings.secret_key.startswith("authentiq-development-secret"):
        logger.warning("Using the development SECRET_KEY. Set AUTHENTIQ_SECRET_KEY before deployment.")
    logger.info("AUTHENTIQ API started in %s mode with %s ledger", settings.environment, ledger_service.adapter.mode)
    yield


app = FastAPI(
    title="AUTHENTIQ API",
    description="Decentralized digital notary and privacy-preserving intellectual property protection.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["Content-Disposition", "Retry-After"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.4f}"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled API error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred"})


@app.get("/api/health", tags=["system"])
def health():
    status = ledger_service.status()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "ledger": {
            "mode": status.get("mode"),
            "label": status.get("label"),
            "connected": status.get("connected"),
            "tamper_detected": status.get("tamper_detected"),
        },
        "zkp": {"scheme": SIGMA_SCHEME, "poseidon": "BN254 Poseidon-254 (circomlib-compatible)"},
        "version": app.version,
    }


app.include_router(api_router, prefix=settings.api_prefix)
