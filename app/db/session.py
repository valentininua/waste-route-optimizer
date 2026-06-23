from __future__ import annotations

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)

if engine.dialect.name == "sqlite" and not settings.allow_sqlite_runtime and "PYTEST_CURRENT_TEST" not in os.environ:
    logger.warning(
        "SQLite DATABASE_URL is active outside tests. SQLite is acceptable for unit tests/local experiments, "
        "but it has degraded concurrent-write behavior and is not recommended for production. "
        "Use PostgreSQL or set ALLOW_SQLITE_RUNTIME=true explicitly."
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
