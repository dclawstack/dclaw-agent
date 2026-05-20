from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_engine_kwargs: dict = {"echo": False, "future": True}
if settings.is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.database_url, **_engine_kwargs)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_sqlite_schema() -> None:
    """Create all tables on a fresh SQLite file.

    Production Postgres should use Alembic migrations; this is a dev convenience
    so `uvicorn` works without a separate `alembic upgrade head` step.
    """
    if not settings.is_sqlite:
        return
    from app.models.base import Base
    import app.models  # noqa: F401 — ensure all models register on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
