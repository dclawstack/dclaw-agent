from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.agent import AgentDefinition
from app.models.user import User
from app.schemas.agent import (
    AgentDefinitionCreate,
    AgentDefinitionOut,
    AgentDefinitionUpdate,
)

router = APIRouter()


async def _require_owner(
    agent_id: UUID, current: User, session: AsyncSession
) -> AgentDefinition:
    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your agent")
    return agent


@router.post("", response_model=AgentDefinitionOut)
async def create_agent(
    payload: AgentDefinitionCreate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> AgentDefinition:
    agent = AgentDefinition(
        id=uuid4(),
        owner_id=current.id,
        name=payload.name,
        description=payload.description,
        nodes=[n.model_dump() for n in payload.nodes],
        edges=[e.model_dump() for e in payload.edges],
        entry_node_id=payload.entry_node_id,
        max_steps=payload.max_steps,
        timeout_seconds=payload.timeout_seconds,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.get("", response_model=list[AgentDefinitionOut])
async def list_agents(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[AgentDefinition]:
    result = await session.execute(
        select(AgentDefinition).where(
            or_(
                AgentDefinition.owner_id == current.id,
                AgentDefinition.is_public.is_(True),
            )
        )
    )
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentDefinitionOut)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> AgentDefinition:
    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != current.id and not agent.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your agent")
    return agent


@router.patch("/{agent_id}", response_model=AgentDefinitionOut)
async def update_agent(
    agent_id: UUID,
    payload: AgentDefinitionUpdate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> AgentDefinition:
    agent = await _require_owner(agent_id, current, session)

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in ("nodes", "edges") and value is not None:
            value = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in value
            ]
        setattr(agent, field, value)

    agent.version += 1
    await session.commit()
    await session.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> None:
    agent = await _require_owner(agent_id, current, session)
    await session.delete(agent)
    await session.commit()


@router.post("/{agent_id}/publish", response_model=AgentDefinitionOut)
async def publish_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> AgentDefinition:
    agent = await _require_owner(agent_id, current, session)
    agent.is_public = True
    await session.commit()
    await session.refresh(agent)
    return agent
