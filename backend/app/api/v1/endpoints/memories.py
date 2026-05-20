import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.memory import Memory
from app.schemas.memory import (
    MemoryConsolidateRequest,
    MemoryConsolidateResponse,
    MemoryCreate,
    MemoryLearnRequest,
    MemoryLearnResponse,
    MemoryOut,
    MemoryRetrieveRequest,
    MemoryStatsOut,
    MemoryUpdate,
)
from app.services.memory import (
    consolidate_memories,
    delete_memory,
    get_session_memories,
    learn_preferences_from_text,
    list_episodic_sessions,
    memory_stats,
    retrieve_memories,
    store_memory,
    update_memory,
)

router = APIRouter()


@router.get("/stats", response_model=MemoryStatsOut)
async def get_memory_stats(
    scope: str = "global",
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Any:
    return await memory_stats(session, scope)


@router.get("/sessions", response_model=list[str])
async def get_episodic_sessions(
    scope: str = "global",
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[str]:
    return await list_episodic_sessions(session, scope)


@router.get("/sessions/{session_id}", response_model=list[MemoryOut])
async def get_session_memories_endpoint(
    session_id: str,
    scope: str = "global",
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[Memory]:
    return await get_session_memories(session, scope, session_id)


@router.get("", response_model=list[MemoryOut])
@router.get("/", response_model=list[MemoryOut])
async def list_memories(
    scope: str = "global",
    memory_type: str | None = None,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[Memory]:
    stmt = select(Memory).where(Memory.scope == scope)
    if memory_type is not None:
        stmt = stmt.where(Memory.memory_type == memory_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Memory:
    return await store_memory(
        session=session,
        scope=payload.scope,
        memory_type=payload.memory_type,
        key=payload.key,
        content=payload.content,
        importance=payload.importance,
        metadata=payload.metadata_,
    )


# NOTE: /retrieve must be placed BEFORE /{memory_id} to avoid route shadowing
@router.post("/retrieve", response_model=list[MemoryOut])
async def retrieve_memories_endpoint(
    payload: MemoryRetrieveRequest,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[Memory]:
    return await retrieve_memories(session, payload.scope, payload.query, payload.top_k)


@router.post("/learn", response_model=MemoryLearnResponse)
async def learn_preferences_endpoint(
    payload: MemoryLearnRequest,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Any:
    learned = await learn_preferences_from_text(
        session, payload.scope, payload.text, payload.session_id
    )
    return {"learned": learned, "count": len(learned)}


@router.post("/consolidate", response_model=MemoryConsolidateResponse)
async def consolidate_memories_endpoint(
    payload: MemoryConsolidateRequest,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Any:
    return await consolidate_memories(session, payload.scope, payload.max_to_keep)


@router.get("/{memory_id}", response_model=MemoryOut)
async def get_memory(
    memory_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
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
    current: User = Depends(get_current_user),
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
    current: User = Depends(get_current_user),
) -> None:
    found = await delete_memory(session, memory_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
