from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.agent import AgentDefinition
from app.models.schedule import ScheduledRun, ScheduledTask
from app.schemas.schedule import (
    ScheduledRunOut,
    ScheduledTaskCreate,
    ScheduledTaskOut,
    ScheduledTaskUpdate,
)
from app.services.task_scheduler import create_scheduled_task_with_next_run

router = APIRouter()


@router.post("/", response_model=ScheduledTaskOut)
async def create_task(
    payload: ScheduledTaskCreate,
    session: AsyncSession = Depends(get_session),
) -> ScheduledTask:
    agent_result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == payload.agent_id)
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    if payload.schedule_type == "cron" and not payload.cron_expr:
        raise HTTPException(status_code=422, detail="cron_expr required for cron schedule")
    if payload.schedule_type == "interval" and not payload.interval_seconds:
        raise HTTPException(status_code=422, detail="interval_seconds required for interval schedule")

    task = ScheduledTask(
        agent_id=payload.agent_id,
        name=payload.name,
        description=payload.description,
        schedule_type=payload.schedule_type,
        cron_expr=payload.cron_expr,
        interval_seconds=payload.interval_seconds,
        input_data=payload.input_data,
        max_retries=payload.max_retries,
        retry_delay_seconds=payload.retry_delay_seconds,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    await create_scheduled_task_with_next_run(session, task)
    return task


@router.get("/", response_model=list[ScheduledTaskOut])
async def list_tasks(
    session: AsyncSession = Depends(get_session),
) -> list[ScheduledTask]:
    result = await session.execute(
        select(ScheduledTask).order_by(ScheduledTask.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=ScheduledTaskOut)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ScheduledTask:
    result = await session.execute(
        select(ScheduledTask).where(ScheduledTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return task


@router.patch("/{task_id}", response_model=ScheduledTaskOut)
async def update_task(
    task_id: UUID,
    payload: ScheduledTaskUpdate,
    session: AsyncSession = Depends(get_session),
) -> ScheduledTask:
    result = await session.execute(
        select(ScheduledTask).where(ScheduledTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(ScheduledTask).where(ScheduledTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    await session.delete(task)
    await session.commit()


@router.post("/{task_id}/pause", response_model=ScheduledTaskOut)
async def pause_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ScheduledTask:
    result = await session.execute(
        select(ScheduledTask).where(ScheduledTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    task.is_active = False
    await session.commit()
    await session.refresh(task)
    return task


@router.post("/{task_id}/resume", response_model=ScheduledTaskOut)
async def resume_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ScheduledTask:
    result = await session.execute(
        select(ScheduledTask).where(ScheduledTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    task.is_active = True
    await create_scheduled_task_with_next_run(session, task)
    return task


@router.get("/{task_id}/runs", response_model=list[ScheduledRunOut])
async def list_task_runs(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ScheduledRun]:
    result = await session.execute(
        select(ScheduledRun)
        .where(ScheduledRun.scheduled_task_id == task_id)
        .order_by(ScheduledRun.scheduled_at.desc())
    )
    return list(result.scalars().all())
