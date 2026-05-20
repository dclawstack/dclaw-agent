import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition, AgentRun
from app.models.schedule import ScheduledRun, ScheduledTask

logger = logging.getLogger(__name__)

SCHEDULER_INTERVAL_SECONDS = 30


def _matches_cron_field(expr: str, value: int) -> bool:
    """Return True if `value` satisfies a single cron field expression."""
    for part in expr.split(","):
        if part == "*":
            return True
        step = 1
        if "/" in part:
            part, step_str = part.split("/", 1)
            step = int(step_str)
        if part == "*":
            lo, hi = 0, 59  # wide range; caller constrains value
            if (value - lo) % step == 0:
                return True
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
        else:
            lo = hi = int(part)
        if lo <= value <= hi and (value - lo) % step == 0:
            return True
    return False


def _next_cron_time(expr: str, after: datetime) -> datetime | None:
    """Compute the next datetime >= after+1min that matches the 5-field cron expression."""
    parts = expr.strip().split()
    if len(parts) != 5:
        return None
    min_e, hour_e, dom_e, month_e, dow_e = parts

    # Advance past current minute so we don't re-fire immediately
    current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

    for _ in range(525_600):  # up to 1 year of minutes
        # cron DOW: 0=Sun, 1=Mon, ..., 6=Sat; Python weekday: 0=Mon, ..., 6=Sun
        cron_dow = (current.weekday() + 1) % 7
        if (
            _matches_cron_field(month_e, current.month)
            and _matches_cron_field(dom_e, current.day)
            and _matches_cron_field(dow_e, cron_dow)
            and _matches_cron_field(hour_e, current.hour)
            and _matches_cron_field(min_e, current.minute)
        ):
            return current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current
        current += timedelta(minutes=1)
    return None


def compute_next_run(task: ScheduledTask, from_time: datetime) -> datetime | None:
    """Return the next scheduled fire time after `from_time`, or None if no recurrence."""
    now = from_time if from_time.tzinfo else from_time.replace(tzinfo=timezone.utc)
    if task.schedule_type == "interval":
        secs = task.interval_seconds or 3600
        return now + timedelta(seconds=secs)
    if task.schedule_type == "cron" and task.cron_expr:
        return _next_cron_time(task.cron_expr, now)
    return None  # "once" tasks have no recurrence


async def create_scheduled_task_with_next_run(
    session: AsyncSession, task: ScheduledTask
) -> None:
    """Set initial next_run_at for a newly created task and persist."""
    now = datetime.now(timezone.utc)
    if task.schedule_type == "once":
        task.next_run_at = now
    else:
        # Compute as if last ran now so we get "first occurrence from now"
        fake_now = now - timedelta(seconds=1)
        task.next_run_at = compute_next_run(task, fake_now)
    session.add(task)
    await session.commit()
    await session.refresh(task)


async def trigger_due_tasks(session: AsyncSession) -> None:
    """Fire all active scheduled tasks whose next_run_at is in the past."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(ScheduledTask).where(
            ScheduledTask.is_active.is_(True),
            ScheduledTask.next_run_at <= now,
            ScheduledTask.next_run_at.is_not(None),
        )
    )
    tasks = result.scalars().all()
    for task in tasks:
        await _fire_task(session, task, now)


async def _fire_task(
    session: AsyncSession, task: ScheduledTask, now: datetime
) -> None:
    """Create a ScheduledRun and kick off the underlying agent run."""
    scheduled_run = ScheduledRun(
        scheduled_task_id=task.id,
        status="running",
        attempt_number=1,
        scheduled_at=task.next_run_at or now,
        started_at=now,
    )
    session.add(scheduled_run)

    task.last_run_at = now
    task.next_run_at = compute_next_run(task, now)

    await session.commit()
    await session.refresh(scheduled_run)

    asyncio.create_task(
        _execute_in_background(task.id, task.agent_id, scheduled_run.id, task.input_data)
    )


async def _execute_in_background(
    task_id: UUID,
    agent_id: UUID,
    scheduled_run_id: UUID,
    input_data: dict,
) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.execution import execute_agent

    async with AsyncSessionLocal() as session:
        agent_result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        run_result = await session.execute(
            select(ScheduledRun).where(ScheduledRun.id == scheduled_run_id)
        )
        scheduled_run = run_result.scalar_one_or_none()

        if not agent or not scheduled_run:
            return

        agent_run = AgentRun(
            agent_id=agent.id,
            agent_version=agent.version,
            status="pending",
            input=input_data,
        )
        session.add(agent_run)
        await session.commit()
        await session.refresh(agent_run)

        scheduled_run.agent_run_id = agent_run.id
        await session.commit()

        try:
            await execute_agent(session, agent_run, agent)
            await session.refresh(agent_run)
            final_status = agent_run.status
        except Exception as exc:
            final_status = "failed"
            logger.exception("Scheduled task %s execution error: %s", task_id, exc)

        now = datetime.now(timezone.utc)
        scheduled_run.status = final_status if final_status in ("completed", "cancelled") else "failed"
        scheduled_run.completed_at = now
        if scheduled_run.status == "failed":
            scheduled_run.error_message = f"Agent run ended with status: {final_status}"
            await _maybe_retry(session, scheduled_run, task_id, agent_id, input_data)
        await session.commit()


async def _maybe_retry(
    session: AsyncSession,
    failed_run: ScheduledRun,
    task_id: UUID,
    agent_id: UUID,
    input_data: dict,
) -> None:
    task_result = await session.execute(
        select(ScheduledTask).where(ScheduledTask.id == task_id)
    )
    task = task_result.scalar_one_or_none()
    if not task or failed_run.attempt_number >= task.max_retries:
        return

    now = datetime.now(timezone.utc)
    retry_at = now + timedelta(seconds=task.retry_delay_seconds)
    retry_run = ScheduledRun(
        scheduled_task_id=task_id,
        status="pending",
        attempt_number=failed_run.attempt_number + 1,
        scheduled_at=retry_at,
    )
    session.add(retry_run)
    # Override next_run_at only if the retry is sooner
    if task.next_run_at is None or retry_at < task.next_run_at:
        task.next_run_at = retry_at
    await session.commit()


async def run_scheduler_loop() -> None:
    """Background loop: poll for due tasks every SCHEDULER_INTERVAL_SECONDS."""
    from app.core.database import AsyncSessionLocal

    while True:
        try:
            await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)
            async with AsyncSessionLocal() as session:
                await trigger_due_tasks(session)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Scheduler loop error (continuing)")
