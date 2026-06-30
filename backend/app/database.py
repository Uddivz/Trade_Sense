"""
TradeSense — Async Database Engine
Configures SQLAlchemy async engine, session factory, and declarative base.
All database access in TradeSense goes through the AsyncSession dependency.
"""
from typing import AsyncGenerator


from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import functions
from datetime import datetime

from app.config import settings


# ── SQLite Compilation Overrides ────────────────────────────────────────────────
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(functions.now, "sqlite")
def compile_now_sqlite(element, compiler, **kw):
    return "strftime('%Y-%m-%d %H:%M:%f', 'now')"


def sqlite_now():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')


# ── Engine ─────────────────────────────────────────────────────────────────────
# pool_size=10, max_overflow=20 are appropriate for MVP load.
# Increase at Phase 2 when horizontal scaling is introduced.
# SQLite does not support connection pooling parameters like pool_size/max_overflow,
# so we conditionalize the engine creation.
if settings.database_url.startswith("sqlite"):
    engine: AsyncEngine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )
    @event.listens_for(engine.sync_engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        dbapi_connection.create_function("now", 0, sqlite_now)
else:
    engine: AsyncEngine = create_async_engine(
        settings.database_url,
        echo=settings.debug,           # SQL logging in development only
        pool_pre_ping=True,            # Validates connections before use (handles DB restarts)
        pool_size=10,
        max_overflow=20,
    )

# ── Session Factory ─────────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,        # Prevent lazy-loading errors after commit
    class_=AsyncSession,
)


# ── Declarative Base ────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy ORM models inherit from this base.
    Import Base in every model file; Alembic env.py reads metadata from here.
    """
    pass


# ── FastAPI Dependency ──────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.
    Automatically commits on success and rolls back on exception.

    Usage:
        @router.get("/example")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Health Helper ───────────────────────────────────────────────────────────────
async def check_db_connection() -> bool:
    """
    Verifies the database is reachable.
    Called by the /health endpoint to report DB status.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
