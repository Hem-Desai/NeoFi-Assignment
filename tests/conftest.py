import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient

from app.db.base import Base, get_db
from app.main import app
from app.core.config import settings


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine):
    """Create a test database session."""
    TestSessionLocal = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def override_get_db(test_db):
    """Override the get_db dependency for testing."""
    async def _override_get_db():
        yield test_db
    
    return _override_get_db


@pytest.fixture
async def client(override_get_db):
    """Create a test client for the FastAPI app."""
    # Override the get_db dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # Remove the override
    app.dependency_overrides = {}


@pytest.fixture(scope="module")
def client():
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
