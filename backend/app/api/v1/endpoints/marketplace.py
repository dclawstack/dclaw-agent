from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.agent import AgentDefinition
from app.schemas.agent import MarketplaceAgentOut

router = APIRouter()


@router.get("", response_model=list[MarketplaceAgentOut])
async def list_marketplace(
    sort: str = "newest",
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    stmt = select(AgentDefinition).where(AgentDefinition.is_public.is_(True))
    if search:
        stmt = stmt.where(AgentDefinition.name.ilike(f"%{search}%"))
    if sort == "newest":
        stmt = stmt.order_by(AgentDefinition.created_at.desc())
    else:
        stmt = stmt.order_by(AgentDefinition.created_at.desc())

    result = await session.execute(stmt)
    agents = result.scalars().all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "owner_name": "Anonymous",
            "install_count": 0,
            "created_at": a.created_at,
        }
        for a in agents
    ]


@router.post("/{agent_id}/install")
async def install_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(AgentDefinition).where(
            AgentDefinition.id == agent_id, AgentDefinition.is_public.is_(True)
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"installed": True, "agent_id": str(agent_id)}


@router.delete("/{agent_id}/install", status_code=204)
async def uninstall_agent(
    agent_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    pass
