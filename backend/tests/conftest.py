import pytest
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from typing import AsyncGenerator


# 1. Define custom compiler rule for PostgreSQL JSONB on SQLite
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


from sqlalchemy.sql import functions

@compiles(functions.now, "sqlite")
def compile_now_sqlite(element, compiler, **kw):
    return "strftime('%Y-%m-%d %H:%M:%f', 'now')"


# 2. Patch app.database module attributes before any imports occur in tests
import app.database
from app.database import Base

TEST_DB_FILE = "test.db"

test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{TEST_DB_FILE}",
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Re-assign database engine and session maker to our mock SQLite implementation
app.database.engine = test_engine
app.database.AsyncSessionLocal = TestSessionLocal


# 3. Override get_db dependency inside the FastAPI app
from app.main import app as fastapi_app

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

fastapi_app.dependency_overrides[app.database.get_db] = override_get_db


# 4. Bootstrap database tables and cleanup file-based SQLite db
@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    # Ensure any old test database file is removed first
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()

    # Clean up the file after tests
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
