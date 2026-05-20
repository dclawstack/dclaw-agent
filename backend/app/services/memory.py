import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory

# ---------------------------------------------------------------------------
# Tokenisation helpers for BM25 retrieval
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of", "and",
    "or", "for", "with", "this", "that", "was", "are", "be", "by", "as",
    "i", "my", "me", "we", "you", "he", "she", "they", "but", "not",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOP_WORDS]


def _bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    avg_doc_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """BM25 term-frequency score without IDF (no corpus stats available)."""
    if not doc_tokens or not query_tokens:
        return 0.0
    tf_map = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    score = 0.0
    for term in set(query_tokens):
        tf = tf_map.get(term, 0)
        if tf == 0:
            continue
        norm = tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1)))
        score += norm
    return score


# ---------------------------------------------------------------------------
# Preference extraction patterns
# ---------------------------------------------------------------------------

_PREF_PATTERNS = [
    re.compile(r"i (?:prefer|like|love|enjoy|always use|want) (.+?)(?:\.|,|;|$)", re.I),
    re.compile(r"i (?:don't|do not|dislike|hate|avoid|never use|never want) (.+?)(?:\.|,|;|$)", re.I),
    re.compile(r"my (?:preferred|favorite|favourite|default) \w+ is (.+?)(?:\.|,|;|$)", re.I),
    re.compile(r"please (?:always|never) (.+?)(?:\.|,|;|$)", re.I),
]


def _extract_preference_phrases(text: str) -> list[str]:
    found: list[str] = []
    for pattern in _PREF_PATTERNS:
        for m in pattern.finditer(text):
            phrase = m.group(1).strip()
            if phrase:
                found.append(phrase)
    return found


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


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

    query_tokens = _tokenize(query)
    now = datetime.now(timezone.utc)

    # Pre-compute average document length for BM25 normalisation
    doc_token_lists = [
        _tokenize(m.content + " " + m.key) for m in memories
    ]
    avg_doc_len = (
        sum(len(t) for t in doc_token_lists) / len(doc_token_lists)
        if doc_token_lists
        else 1.0
    )

    scored: list[tuple[float, Memory]] = []
    for mem, doc_tokens in zip(memories, doc_token_lists):
        bm25 = _bm25_score(query_tokens, doc_tokens, avg_doc_len)

        created = mem.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_seconds = max((now - created).total_seconds(), 1)
        recency = 1.0 / (1.0 + age_seconds / 86400.0)

        score = (bm25 * mem.importance) + recency * 0.1
        scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [m for _, m in scored[:top_k]]

    for mem in top:
        mem.access_count = (mem.access_count or 0) + 1
        mem.last_accessed_at = now
    await session.commit()

    return top


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


# ---------------------------------------------------------------------------
# Summarisation
# ---------------------------------------------------------------------------


async def summarize_context(text: str) -> str:
    """Summarise text to at most ~3 sentences via Ollama; falls back gracefully."""
    if len(text) <= 500:
        return text
    from app.services.execution import call_ollama

    chunks = [text[i : i + 4000] for i in range(0, min(len(text), 12000), 4000)]
    summaries: list[str] = []
    for chunk in chunks:
        prompt = f"Summarize concisely in 2-3 sentences:\n\n{chunk}"
        summaries.append(await call_ollama(prompt))
    if len(summaries) == 1:
        return summaries[0]
    combined = " ".join(summaries)
    prompt = f"Combine into one concise paragraph:\n\n{combined}"
    return await call_ollama(prompt)


# ---------------------------------------------------------------------------
# User preference learning
# ---------------------------------------------------------------------------


async def learn_preferences_from_text(
    session: AsyncSession,
    scope: str,
    text: str,
    session_id: str | None = None,
) -> list[Memory]:
    """Extract preference signals from text and persist them as 'preference' memories."""
    phrases = _extract_preference_phrases(text)
    stored: list[Memory] = []
    for phrase in phrases:
        key = f"pref:{phrase[:80]}"
        # Deduplicate: check if an equivalent preference already exists
        existing = await session.execute(
            select(Memory).where(
                Memory.scope == scope,
                Memory.memory_type == "preference",
                Memory.key == key,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue
        meta: dict[str, Any] = {"source": "auto_learned"}
        if session_id:
            meta["session_id"] = session_id
        mem = await store_memory(
            session=session,
            scope=scope,
            memory_type="preference",
            key=key,
            content=phrase,
            importance=0.8,
            metadata=meta,
        )
        stored.append(mem)
    return stored


# ---------------------------------------------------------------------------
# Episodic session helpers
# ---------------------------------------------------------------------------


async def list_episodic_sessions(
    session: AsyncSession,
    scope: str,
) -> list[str]:
    """Return distinct session_ids from episodic memory metadata for a scope."""
    result = await session.execute(
        select(Memory).where(
            Memory.scope == scope,
            Memory.memory_type == "episodic",
        ).order_by(Memory.created_at.asc())
    )
    memories = list(result.scalars().all())
    seen: list[str] = []
    seen_set: set[str] = set()
    for mem in memories:
        sid = (mem.metadata_ or {}).get("session_id")
        if sid and sid not in seen_set:
            seen.append(str(sid))
            seen_set.add(str(sid))
    return seen


async def get_session_memories(
    session: AsyncSession,
    scope: str,
    session_id: str,
) -> list[Memory]:
    """Return all episodic memories for a specific session, in creation order."""
    result = await session.execute(
        select(Memory).where(
            Memory.scope == scope,
            Memory.memory_type == "episodic",
        ).order_by(Memory.created_at.asc())
    )
    all_mems = list(result.scalars().all())
    return [
        m for m in all_mems
        if (m.metadata_ or {}).get("session_id") == session_id
    ]


# ---------------------------------------------------------------------------
# Memory consolidation
# ---------------------------------------------------------------------------


async def consolidate_memories(
    session: AsyncSession,
    scope: str,
    max_to_keep: int = 100,
) -> dict[str, int]:
    """
    Prune low-importance, rarely-accessed memories when over the limit.

    Returns counts of deleted and remaining memories.
    """
    result = await session.execute(
        select(Memory).where(Memory.scope == scope)
        .order_by(Memory.importance.asc(), Memory.access_count.asc(), Memory.created_at.asc())
    )
    memories = list(result.scalars().all())
    total = len(memories)
    if total <= max_to_keep:
        return {"deleted": 0, "remaining": total}

    to_delete = memories[: total - max_to_keep]
    for mem in to_delete:
        await session.delete(mem)
    await session.commit()
    return {"deleted": len(to_delete), "remaining": total - len(to_delete)}


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


async def memory_stats(
    session: AsyncSession,
    scope: str,
) -> dict[str, Any]:
    """Return aggregate statistics for memories in a scope."""
    result = await session.execute(
        select(Memory.memory_type, func.count(Memory.id)).where(
            Memory.scope == scope
        ).group_by(Memory.memory_type)
    )
    rows = result.all()
    by_type = {row[0]: row[1] for row in rows}
    total = sum(by_type.values())

    # Average importance
    imp_result = await session.execute(
        select(func.avg(Memory.importance)).where(Memory.scope == scope)
    )
    avg_importance = imp_result.scalar() or 0.0

    return {
        "total": total,
        "by_type": by_type,
        "avg_importance": round(float(avg_importance), 3),
    }
