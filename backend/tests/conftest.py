"""Pytest configuration and fixtures"""
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.api.deps import get_db  # This is the get_db used by API endpoints
# Import models so they are registered with Base.metadata
from app.models.drug import Drug, DrugVector  # noqa: F401

# Test database - use absolute path for reliability
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_db.sqlite")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
test_async_session_maker = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Drug.__table__.create(sync_conn, checkfirst=True))

    async with test_async_session_maker() as session:
        yield session

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Drug.__table__.drop(sync_conn, checkfirst=True))


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""

    async def override_get_db():
        # Create a new session for each request using the test engine
        async with test_async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def pytest_sessionfinish(session, exitstatus):
    """Clean up test database file after tests"""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
