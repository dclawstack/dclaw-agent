import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory


async def store_memory(
    session: AsyncSession,
    scope: str,
    memory_type: str,
    key: str,
    content: str,
    importance: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> Memory:
    mem = Memory(
        id=uuid.uuid4(),
        scope=scope,
        memory_type=memory_type,
        key=key,
        content=content,
        importance=importance,
        metadata_=metadata if metadata is not None else {},
    )
    session.add(mem)
    await session.commit()
    await session.refresh(mem)
    return mem


async def retrieve_memories(
    session: AsyncSession,
    scope: str,
    query: str,
    top_k: int = 5,
) -> list[Memory]:
    result = await session.execute(
        select(Memory).where(Memory.scope == scope)
    )
    memories = list(result.scalars().all())

    query_words = set(query.lower().split())

    now = datetime.now(timezone.utc)

    scored: list[tuple[float, Memory]] = []
    for mem in memories:
        # Keyword overlap score
        haystack = (mem.content.lower() + " " + mem.key.lower())
        overlap = sum(1 for w in query_words if w in haystack)

        # Recency score: newer memories score higher
        # created_at may be offset-naive from the DB; handle both
        created = mem.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_seconds = max((now - created).total_seconds(), 1)
        recency = 1.0 / (1.0 + age_seconds / 86400.0)  # decay over days

        score = (overlap * mem.importance) + recency * 0.1
        scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [m for _, m in scored[:top_k]]

    # Update access metadata for retrieved memories
    for mem in top:
        mem.access_count = (mem.access_count or 0) + 1
        mem.last_accessed_at = now
    await session.commit()

    return top


async def summarize_context(text: str) -> str:
    if len(text) <= 500:
        return text
    from app.services.execution import call_ollama
    prompt = f"Summarize concisely in 2-3 sentences:\n\n{text[:4000]}"
    return await call_ollama(prompt)


async def delete_memory(session: AsyncSession, memory_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id)
    )
    mem = result.scalar_one_or_none()
    if mem is None:
        return False
    await session.delete(mem)
    await session.commit()
    return True


async def update_memory(
    session: AsyncSession,
    memory_id: uuid.UUID,
    content: str | None = None,
    importance: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> Memory | None:
    result = await session.execute(
        select(Memory).where(Memory.id == memory_id)
    )
    mem = result.scalar_one_or_none()
    if mem is None:
        return None
    if content is not None:
        mem.content = content
    if importance is not None:
        mem.importance = importance
    if metadata is not None:
        mem.metadata_ = metadata
    await session.commit()
    await session.refresh(mem)
    return mem
