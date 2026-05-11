"""
Pytest fixtures for the Knowledge Assistant test suite.
Provides async database sessions, test client, and authenticated users.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app
from app.models.user import User
from app.utils.security import create_access_token, hash_password


# ── Test Database ──
TEST_DB_URL = "sqlite+aiosqlite:///./data/test_knowledge_assistant.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Override the default event loop fixture for session scope."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for tests."""
    async with test_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a standard test user."""
    user = User(
        email="testuser@company.com",
        username="testuser",
        hashed_password=hash_password("TestPassword123!"),
        role="engineer",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@company.com",
        username="admin",
        hashed_password=hash_password("AdminPassword123!"),
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def hr_user(db_session: AsyncSession) -> User:
    """Create an HR test user."""
    user = User(
        email="hr@company.com",
        username="hr_manager",
        hashed_password=hash_password("HRPassword123!"),
        role="hr",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    """Generate Authorization headers for a given user."""
    token = create_access_token(data={"sub": user.id})
    return {"Authorization": f"Bearer {token}"}
