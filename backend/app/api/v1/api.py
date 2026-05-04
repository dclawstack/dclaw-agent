from fastapi import APIRouter

from app.api.v1.endpoints import agents, marketplace, runs

router = APIRouter(prefix="/api/v1/agent")
router.include_router(agents.router, prefix="/agents", tags=["agents"])
router.include_router(runs.router, prefix="/runs", tags=["runs"])
router.include_router(
    marketplace.router, prefix="/marketplace", tags=["marketplace"]
)
