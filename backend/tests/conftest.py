import os
import uuid

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import get_db
from app.core.security import hash_password
from app.models.agent import Base
from app.models.tool import Tool
from app.models.user import User
from app.services.tool_registry import BUILTIN_TOOLS

# Models must be imported before metadata.create_all so tables register.
from app.models.team import AgentTeam, TeamRun  # noqa: F401
from app.models.memory import Memory  # noqa: F401
from app.models.marketplace_install import MarketplaceInstall  # noqa: F401

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/dclaw_agent_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


async def override_get_db():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        for td in BUILTIN_TOOLS:
            r = await session.execute(select(Tool).where(Tool.slug == td["slug"]))
            if not r.scalar_one_or_none():
                session.add(Tool(**td))
        await session.commit()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def auth_user() -> tuple[User, str]:
    """Create a test user and return (user, JWT)."""
    from app.core.security import create_access_token

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        user = User(
            email=f"test-{uuid.uuid4().hex}@example.com",
            display_name="Test User",
            password_hash=hash_password("test-password-1234"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user, create_access_token(str(user.id))


@pytest_asyncio.fixture
async def client(auth_user):
    user, token = auth_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def anon_client():
    """Unauthenticated client for endpoints that should remain public."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
