from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    marketplace,
    memories,
    runs,
    scheduled_tasks,
    teams,
    tools,
)

router = APIRouter(prefix="/api/v1/agent")
router.include_router(agents.router, prefix="/agents", tags=["agents"])
router.include_router(runs.router, prefix="/runs", tags=["runs"])
router.include_router(
    marketplace.router, prefix="/marketplace", tags=["marketplace"]
)
router.include_router(tools.router, prefix="/tools", tags=["tools"])
router.include_router(teams.router, prefix="/teams", tags=["teams"])
router.include_router(memories.router, prefix="/memories", tags=["memories"])
router.include_router(
    scheduled_tasks.router, prefix="/scheduled-tasks", tags=["scheduled-tasks"]
)
