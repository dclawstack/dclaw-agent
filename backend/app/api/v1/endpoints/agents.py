from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.agent import AgentDefinition
from app.schemas.agent import (
    AgentDefinitionCreate,
    AgentDefinitionOut,
    AgentDefinitionUpdate,
)

router = APIRouter()


@router.post("", response_model=AgentDefinitionOut)
async def create_agent(
    payload: AgentDefinitionCreate,
    session: AsyncSession = Depends(get_session),
) -> AgentDefinition:
    agent = AgentDefinition(
        id=uuid4(),
        owner_id=uuid4(),
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
) -> list[AgentDefinition]:
    result = await session.execute(select(AgentDefinition))
    return list(result.scalars().all())


@router.get("/{agent_id}", response_model=AgentDefinitionOut)
async def get_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AgentDefinition:
    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentDefinitionOut)
async def update_agent(
    agent_id: UUID,
    payload: AgentDefinitionUpdate,
    session: AsyncSession = Depends(get_session),
) -> AgentDefinition:
    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

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
) -> None:
    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.delete(agent)
    await session.commit()


@router.post("/{agent_id}/publish", response_model=AgentDefinitionOut)
async def publish_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AgentDefinition:
    result = await session.execute(
        select(AgentDefinition).where(AgentDefinition.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_public = True
    await session.commit()
    await session.refresh(agent)
    return agent
