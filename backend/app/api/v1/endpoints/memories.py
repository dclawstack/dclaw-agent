import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryOut, MemoryRetrieveRequest, MemoryUpdate
from app.services.memory import delete_memory, retrieve_memories, store_memory, update_memory

router = APIRouter()


@router.get("/", response_model=list[MemoryOut])
async def list_memories(
    scope: str = "global",
    memory_type: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Memory]:
    stmt = select(Memory).where(Memory.scope == scope)
    if memory_type is not None:
        stmt = stmt.where(Memory.memory_type == memory_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    session: AsyncSession = Depends(get_session),
) -> Memory:
    mem = await store_memory(
        session=session,
        scope=payload.scope,
        memory_type=payload.memory_type,
        key=payload.key,
        content=payload.content,
        importance=payload.importance,
        metadata=payload.metadata_,
    )
    return mem


# NOTE: /retrieve must be placed BEFORE /{memory_id} to avoid route shadowing
@router.post("/retrieve", response_model=list[MemoryOut])
async def retrieve_memories_endpoint(
    payload: MemoryRetrieveRequest,
    session: AsyncSession = Depends(get_session),
) -> list[Memory]:
    return await retrieve_memories(session, payload.scope, payload.query, payload.top_k)


@router.get("/{memory_id}", response_model=MemoryOut)
async def get_memory(
    memory_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Memory:
    result = await session.execute(select(Memory).where(Memory.id == memory_id))
    mem = result.scalar_one_or_none()
    if mem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return mem


@router.patch("/{memory_id}", response_model=MemoryOut)
async def patch_memory(
    memory_id: uuid.UUID,
    payload: MemoryUpdate,
    session: AsyncSession = Depends(get_session),
) -> Memory:
    mem = await update_memory(
        session=session,
        memory_id=memory_id,
        content=payload.content,
        importance=payload.importance,
        metadata=payload.metadata_,
    )
    if mem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return mem


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_memory(
    memory_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    found = await delete_memory(session, memory_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
