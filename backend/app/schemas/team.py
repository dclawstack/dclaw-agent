from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeamStep(BaseModel):
    agent_id: str
    role: str
    order: int
    system_prompt: str | None = None


class TeamCreate(BaseModel):
    name: str
    description: str | None = None
    workflow_type: str = "sequential"
    steps: list[TeamStep]


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list[TeamStep] | None = None


class TeamRunCreate(BaseModel):
    input: dict[str, Any]
    wait_for_completion: bool = False


class TeamRunLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: str
    role: str
    message: str


class TeamRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    status: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    step_outputs: dict[str, Any]
    logs: list[dict[str, Any]]
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime


class AgentTeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    workflow_type: str
    steps: list[TeamStep]
    created_at: datetime
    updated_at: datetime
