"""Versioned API request and response contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateSessionResponse(BaseModel):
    session_id: UUID
    created_at: datetime
    status: str


class PrepareActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Any = None
    account_id: Any = None
    account_name: Any = None
    amount: Any = None
    close_date: Any = None
    stage_name: Any = None


class ValidationErrorItem(BaseModel):
    field: str
    code: str
    message: str


class PrepareActionResponse(BaseModel):
    action_id: UUID
    session_id: UUID
    status: str
    expires_at: datetime
    confirmation_summary: dict[str, str]
    replayed: bool = False


class ConfirmActionResponse(BaseModel):
    action_id: UUID
    status: str
    crm_record_id: str
    replayed: bool = False
