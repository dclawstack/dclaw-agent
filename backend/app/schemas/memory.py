from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreate(BaseModel):
    scope: str = "global"
    memory_type: Literal["episodic", "semantic", "preference"] = "episodic"
    key: str
    content: str
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    importance: float = 0.5

    model_config = ConfigDict(populate_by_name=True)


class MemoryUpdate(BaseModel):
    content: str | None = None
    importance: float | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class MemoryRetrieveRequest(BaseModel):
    scope: str = "global"
    query: str
    top_k: int = 5


class MemoryOut(BaseModel):
    id: UUID
    scope: str
    memory_type: str
    key: str
    content: str
    metadata_: dict[str, Any] = Field(alias="metadata")
    importance: float
    access_count: int
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
