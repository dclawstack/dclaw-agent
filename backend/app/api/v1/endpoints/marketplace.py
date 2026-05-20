import uuid
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.agent import AgentDefinition
from app.models.marketplace_install import MarketplaceInstall
from app.schemas.agent import MarketplaceAgentOut

router = APIRouter()

ANONYMOUS_INSTALLER = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _short_owner_name(owner_id: uuid.UUID) -> str:
    return f"user-{str(owner_id)[:8]}"


def _install_count_subq():
    return (
        select(
            MarketplaceInstall.agent_id.label("agent_id"),
            func.count(MarketplaceInstall.id).label("install_count"),
        )
        .group_by(MarketplaceInstall.agent_id)
        .subquery()
    )


@router.get("", response_model=list[MarketplaceAgentOut])
async def list_marketplace(
    sort: str = "newest",
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    install_counts = _install_count_subq()
    stmt = (
        select(AgentDefinition, func.coalesce(install_counts.c.install_count, 0))
        .outerjoin(install_counts, install_counts.c.agent_id == AgentDefinition.id)
        .where(AgentDefinition.is_public.is_(True))
    )
    if search:
        stmt = stmt.where(AgentDefinition.name.ilike(f"%{search}%"))
    if sort == "installs":
        stmt = stmt.order_by(func.coalesce(install_counts.c.install_count, 0).desc())
    else:  # newest
        stmt = stmt.order_by(AgentDefinition.created_at.desc())

    result = await session.execute(stmt)
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "owner_name": _short_owner_name(agent.owner_id),
            "install_count": int(count),
            "created_at": agent.created_at,
        }
        for agent, count in result.all()
    ]


@router.post("/{agent_id}/install")
async def install_agent(
    agent_id: UUID,
    installer_id: UUID | None = Body(default=None, embed=True),
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

    install = MarketplaceInstall(
        agent_id=agent_id,
        installer_id=installer_id or ANONYMOUS_INSTALLER,
    )
    session.add(install)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # already installed by this installer — idempotent
    count_row = await session.execute(
        select(func.count(MarketplaceInstall.id)).where(
            MarketplaceInstall.agent_id == agent_id
        )
    )
    return {
        "installed": True,
        "agent_id": str(agent_id),
        "install_count": int(count_row.scalar_one()),
    }


@router.delete("/{agent_id}/install", status_code=204)
async def uninstall_agent(
    agent_id: UUID,
    installer_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> None:
    target_installer = installer_id or ANONYMOUS_INSTALLER
    await session.execute(
        delete(MarketplaceInstall).where(
            MarketplaceInstall.agent_id == agent_id,
            MarketplaceInstall.installer_id == target_installer,
        )
    )
    await session.commit()
