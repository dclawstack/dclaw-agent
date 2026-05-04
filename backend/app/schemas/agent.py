from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentNode(BaseModel):
    id: str
    type: Literal["llm", "tool", "memory", "condition", "loop", "input", "output"]
    label: str
    position: dict[str, float]
    config: dict[str, Any]


class AgentEdge(BaseModel):
    id: str
    source: str
    target: str
    condition: str | None = None


class AgentDefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    nodes: list[AgentNode]
    edges: list[AgentEdge]
    entry_node_id: str
    max_steps: int = 50
    timeout_seconds: int = 300


class AgentDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: list[AgentNode] | None = None
    edges: list[AgentEdge] | None = None
    entry_node_id: str | None = None
    max_steps: int | None = None
    timeout_seconds: int | None = None
    is_public: bool | None = None


class AgentDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    nodes: list[AgentNode]
    edges: list[AgentEdge]
    entry_node_id: str
    max_steps: int
    timeout_seconds: int
    is_public: bool
    version: int
    created_at: datetime
    updated_at: datetime


class AgentRunCreate(BaseModel):
    input: dict[str, Any]
    wait_for_completion: bool = False


class StepLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_number: int
    node_id: str
    node_type: str
    status: Literal["running", "completed", "failed", "skipped"]
    input: dict[str, Any] | None
    output: dict[str, Any] | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    agent_version: int
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    step_count: int
    input: dict[str, Any]
    output: dict[str, Any] | None
    created_at: datetime
    steps: list[StepLogOut] | None = None


class MarketplaceAgentOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_name: str
    install_count: int
    created_at: datetime
