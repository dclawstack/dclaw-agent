from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ScheduledTaskCreate(BaseModel):
    agent_id: UUID
    name: str
    description: str | None = None
    schedule_type: str  # "cron" | "interval" | "once"
    cron_expr: str | None = None
    interval_seconds: int | None = None
    input_data: dict[str, Any] = {}
    max_retries: int = 3
    retry_delay_seconds: int = 60


class ScheduledTaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cron_expr: str | None = None
    interval_seconds: int | None = None
    input_data: dict[str, Any] | None = None
    max_retries: int | None = None
    retry_delay_seconds: int | None = None
    is_active: bool | None = None


class ScheduledRunOut(BaseModel):
    id: UUID
    scheduled_task_id: UUID
    agent_run_id: UUID | None
    status: str
    attempt_number: int
    error_message: str | None
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduledTaskOut(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    description: str | None
    schedule_type: str
    cron_expr: str | None
    interval_seconds: int | None
    input_data: dict[str, Any]
    max_retries: int
    retry_delay_seconds: int
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    scheduled_runs: list[ScheduledRunOut] = []

    model_config = {"from_attributes": True}
