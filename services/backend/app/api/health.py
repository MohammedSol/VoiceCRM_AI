"""Health-check route — Sprint 0."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """Return 200 with service status. No external dependencies checked here."""
    return HealthResponse(status="ok", version="0.1.0")
