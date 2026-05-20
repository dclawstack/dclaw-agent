import asyncio
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.api.deps import get_session
from app.core.database import AsyncSessionLocal
from app.models.agent import AgentDefinition, AgentRun
from app.schemas.agent import AgentRunCreate, AgentRunOut, AgentRunSummary
from app.services.execution import execute_agent

router = APIRouter()


@router.get("", response_model=list[AgentRunSummary])
@router.get("/", response_model=list[AgentRunSummary])
async def list_runs(
    agent_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> list[AgentRun]:
    limit = max(1, min(limit, 200))
    stmt = select(AgentRun).order_by(AgentRun.started_at.desc())
    if agent_id is not None:
        stmt = stmt.where(AgentRun.agent_id == agent_id)
    if status is not None:
        stmt = stmt.where(AgentRun.status == status)
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def run_in_background(run_id: UUID, agent_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        run = result.scalar_one()
        result2 = await session.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        agent = result2.scalar_one()
        await execute_agent(session, run, agent)


@router.post("/{agent_id}/runs", response_model=AgentRunOut)
async def create_run(
    agent_id: UUID,
    payload: AgentRunCreate,
    session: AsyncSession = Depends(get_session),
) -> AgentRun:
    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    run = AgentRun(
        agent_id=agent.id,
        agent_version=agent.version,
        status="pending",
        input=payload.input,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    if payload.wait_for_completion:
        await execute_agent(session, run, agent)
        await session.refresh(run)
    else:
        asyncio.create_task(run_in_background(run.id, agent.id))

    return run


@router.get("/{run_id}", response_model=AgentRunOut)
async def get_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AgentRun:
    result = await session.execute(
        select(AgentRun).where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/cancel", response_model=AgentRunOut)
async def cancel_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AgentRun:
    result = await session.execute(
        select(AgentRun).where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status == "running":
        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(run)
    return run


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    result = await session.execute(
        select(AgentRun).where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        yield f"event: run_started\ndata: {{\"run_id\":\"{run_id}\"}}\n\n"
        for _ in range(60):
            await session.refresh(run)
            if run.status in ("completed", "failed", "cancelled"):
                yield (
                    f"event: run_completed\ndata: "
                    f"{{\"status\":\"{run.status}\",\"duration_ms\":{run.duration_ms or 0}}}\n\n"
                )
                return
            await asyncio.sleep(1)
        yield f"event: run_completed\ndata: {{\"status\":\"timeout\"}}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream"
    )
