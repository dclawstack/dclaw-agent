from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.tool import Tool
from app.schemas.tool import ToolExecuteRequest, ToolOut
from app.services.tool_registry import execute_builtin_tool

router = APIRouter()


@router.get("", response_model=list[ToolOut])
async def list_tools(
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[Tool]:
    result = await session.execute(select(Tool))
    return list(result.scalars().all())


@router.get("/{slug}", response_model=ToolOut)
async def get_tool(
    slug: str,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Tool:
    result = await session.execute(select(Tool).where(Tool.slug == slug))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.post("/{slug}/install", response_model=ToolOut)
async def install_tool(
    slug: str,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Tool:
    result = await session.execute(select(Tool).where(Tool.slug == slug))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool.is_installed = True
    await session.commit()
    await session.refresh(tool)
    return tool


@router.delete("/{slug}/install", status_code=204)
async def uninstall_tool(
    slug: str,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> None:
    result = await session.execute(select(Tool).where(Tool.slug == slug))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool.is_installed = False
    await session.commit()


@router.post("/{slug}/execute")
async def execute_tool(
    slug: str,
    payload: ToolExecuteRequest,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await session.execute(select(Tool).where(Tool.slug == slug))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return await execute_builtin_tool(slug, payload.inputs)
