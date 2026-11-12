from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine_options = {"pool_pre_ping": True, "future": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
elif settings.is_postgres:
    engine_options["pool_recycle"] = 280
    engine_options["connect_args"] = {"connect_timeout": 15}

engine = create_engine(settings.database_url, **engine_options)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import Base

    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)

    from app.core.migrations import ensure_schema

    ensure_schema()
