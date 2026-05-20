import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.v1.api import router as api_router
from app.core.database import AsyncSessionLocal, engine
from app.core.logging import configure_logging, get_logger
from app.models.agent import Base
from app.models.tool import Tool  # noqa: F401 — registers Tool with Base metadata
from app.models.team import AgentTeam, TeamRun  # noqa: F401 — registers team models with Base metadata
from app.models.memory import Memory  # noqa: F401 — registers Memory with Base metadata

configure_logging()
log = get_logger(__name__)


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
    log.info("app_starting")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_tools()
    log.info("app_ready")
    yield
    log.info("app_stopping")
    from app.services.run_supervisor import supervisor
    await supervisor.shutdown()
    await engine.dispose()


app = FastAPI(title="DClaw Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    start = time.perf_counter()
    log.info("request_started")
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_failed")
        raise
    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("request_completed", status_code=response.status_code, duration_ms=duration_ms)
    response.headers["x-request-id"] = request_id
    return response


app.include_router(api_router)
app.include_router(health_router)
