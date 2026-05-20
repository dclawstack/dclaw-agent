"""Healthchecks split into liveness vs. readiness.

- /health/live   — always 200 if the process is up (Kubernetes liveness)
- /health/ready  — 200 only when dependencies are reachable (readiness)
- /health        — alias for /health/ready, kept for backward compat
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

router = APIRouter()


async def _check_db() -> tuple[str, str | None]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok", None
    except Exception as exc:
        return "down", str(exc)[:200]


async def _check_ollama() -> tuple[str, str | None]:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            resp.raise_for_status()
        return "ok", None
    except Exception as exc:
        return "down", str(exc)[:200]


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
@router.get("/health/")
@router.get("/health")
async def readiness(response: Response) -> dict[str, Any]:
    db_status, db_err = await _check_db()
    ollama_status, ollama_err = await _check_ollama()

    deps = {
        "db": {"status": db_status, "error": db_err},
        "ollama": {"status": ollama_status, "error": ollama_err},
    }
    required_ok = db_status == "ok"

    if not required_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "deps": deps}

    return {"status": "ok", "deps": deps}
