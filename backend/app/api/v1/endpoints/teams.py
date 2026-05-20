import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.core.database import AsyncSessionLocal
from app.models.team import AgentTeam, TeamRun
from app.models.user import User
from app.schemas.team import AgentTeamOut, TeamCreate, TeamRunCreate, TeamRunOut, TeamUpdate
from app.services.multi_agent import execute_team

router = APIRouter()


async def run_team_in_background(run_id: UUID, team_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TeamRun).where(TeamRun.id == run_id)
        )
        team_run = result.scalar_one()
        result2 = await session.execute(
            select(AgentTeam).where(AgentTeam.id == team_id)
        )
        team = result2.scalar_one()
        await execute_team(session, team_run, team)


@router.post("", response_model=AgentTeamOut)
async def create_team(
    payload: TeamCreate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> AgentTeam:
    team = AgentTeam(
        name=payload.name,
        description=payload.description,
        workflow_type=payload.workflow_type,
        steps=[s.model_dump() for s in payload.steps],
    )
    session.add(team)
    await session.commit()
    await session.refresh(team)
    return team


@router.get("", response_model=list[AgentTeamOut])
async def list_teams(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[AgentTeam]:
    result = await session.execute(select(AgentTeam))
    return list(result.scalars().all())


@router.get("/{team_id}/runs", response_model=list[TeamRunOut])
async def list_team_runs(
    team_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[TeamRun]:
    result = await session.execute(
        select(TeamRun)
        .where(TeamRun.team_id == team_id)
        .order_by(TeamRun.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/runs/{run_id}", response_model=TeamRunOut)
async def get_team_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> TeamRun:
    result = await session.execute(
        select(TeamRun).where(TeamRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Team run not found")
    return run


@router.get("/{team_id}", response_model=AgentTeamOut)
async def get_team(
    team_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> AgentTeam:
    result = await session.execute(
        select(AgentTeam).where(AgentTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.patch("/{team_id}", response_model=AgentTeamOut)
async def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> AgentTeam:
    result = await session.execute(
        select(AgentTeam).where(AgentTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    data = payload.model_dump(exclude_unset=True)
    if "steps" in data and data["steps"] is not None:
        data["steps"] = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in payload.steps  # type: ignore[union-attr]
        ]
    for field, value in data.items():
        setattr(team, field, value)

    await session.commit()
    await session.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> None:
    result = await session.execute(
        select(AgentTeam).where(AgentTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    await session.delete(team)
    await session.commit()


@router.post("/{team_id}/runs", response_model=TeamRunOut)
async def create_team_run(
    team_id: UUID,
    payload: TeamRunCreate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> TeamRun:
    result = await session.execute(
        select(AgentTeam).where(AgentTeam.id == team_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    team_run = TeamRun(
        team_id=team.id,
        status="pending",
        input=payload.input,
        step_outputs={},
        logs=[],
    )
    session.add(team_run)
    await session.commit()
    await session.refresh(team_run)

    if payload.wait_for_completion:
        await execute_team(session, team_run, team)
        await session.refresh(team_run)
    else:
        from app.services.run_supervisor import supervisor

        supervisor.schedule(
            team_run.id, lambda: run_team_in_background(team_run.id, team.id)
        )

    return team_run
