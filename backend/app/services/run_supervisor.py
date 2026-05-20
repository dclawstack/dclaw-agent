"""Tracks background run tasks so we can cancel them and await on shutdown.

The previous code used `asyncio.create_task(...)` without holding the result,
which meant:
  - the task could be garbage-collected before completion
  - cancel was racy (we set the DB status but the worker kept running)
  - lifespan shutdown wouldn't wait for in-flight runs

This module provides a single process-wide RunSupervisor.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable
from uuid import UUID

from app.core.logging import get_logger

log = get_logger(__name__)


class RunSupervisor:
    def __init__(self) -> None:
        self._tasks: dict[UUID, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def schedule(self, run_id: UUID, coro_factory: Callable[[], Awaitable[None]]) -> asyncio.Task:
        task = asyncio.create_task(self._run(run_id, coro_factory()))
        self._tasks[run_id] = task
        log.info("run_scheduled", run_id=str(run_id), active=len(self._tasks))
        return task

    async def _run(self, run_id: UUID, awaitable: Awaitable[None]) -> None:
        try:
            await awaitable
        except asyncio.CancelledError:
            log.info("run_cancelled", run_id=str(run_id))
            raise
        except Exception:
            log.exception("run_crashed", run_id=str(run_id))
        finally:
            async with self._lock:
                self._tasks.pop(run_id, None)

    async def cancel(self, run_id: UUID) -> bool:
        task = self._tasks.get(run_id)
        if task is None or task.done():
            return False
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        return True

    def is_running(self, run_id: UUID) -> bool:
        task = self._tasks.get(run_id)
        return bool(task and not task.done())

    async def shutdown(self) -> None:
        if not self._tasks:
            return
        log.info("supervisor_shutdown_waiting", active=len(self._tasks))
        tasks = list(self._tasks.values())
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()


supervisor = RunSupervisor()
