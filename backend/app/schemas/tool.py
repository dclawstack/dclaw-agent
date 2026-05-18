from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ToolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    description: str | None
    category: str
    config_schema: dict[str, Any]
    is_builtin: bool
    is_installed: bool
    created_at: datetime
    updated_at: datetime


class ToolExecuteRequest(BaseModel):
    inputs: dict[str, Any]
