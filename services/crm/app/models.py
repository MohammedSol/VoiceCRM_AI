"""Typed CRM records and write payloads."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Account(BaseModel):
    """Salesforce account exposed to callers."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str


class Opportunity(BaseModel):
    """Salesforce opportunity exposed to callers."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    account_id: str | None = None
    account_name: str | None = None
    amount: Decimal | None = None
    close_date: date | None = None
    stage_name: str


class OpportunityDraft(BaseModel):
    """Fields required to create an opportunity."""

    name: str = Field(min_length=1, max_length=120)
    account_id: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    close_date: date
    stage_name: str = Field(min_length=1)
