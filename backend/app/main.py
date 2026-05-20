import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import router as api_router
from app.core.database import AsyncSessionLocal, engine
from app.models.agent import Base
from app.models.tool import Tool  # noqa: F401 — registers Tool with Base metadata
from app.models.team import AgentTeam, TeamRun  # noqa: F401 — registers team models with Base metadata
from app.models.memory import Memory  # noqa: F401 — registers Memory with Base metadata
from app.models.schedule import ScheduledTask, ScheduledRun  # noqa: F401 — registers schedule models with Base metadata


async def _seed_tools() -> None:
    from app.services.tool_registry import BUILTIN_TOOLS
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        for td in BUILTIN_TOOLS:
            r = await session.execute(select(Tool).where(Tool.slug == td["slug"]))
            if not r.scalar_one_or_none():
                session.add(Tool(**td))
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_tools()
    from app.services.task_scheduler import run_scheduler_loop
    scheduler_task = asyncio.create_task(run_scheduler_loop())
    yield
    scheduler_task.cancel()
    await engine.dispose()


app = FastAPI(title="DClaw Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
