"""Persistence operations for the session/action workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AuditLogRecord, PendingActionRecord, SessionRecord


class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(self) -> SessionRecord:
        record = SessionRecord()
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_session(self, session_id: UUID) -> SessionRecord | None:
        return await self.session.get(SessionRecord, session_id)

    async def get_action(self, action_id: UUID) -> PendingActionRecord | None:
        return await self.session.get(PendingActionRecord, action_id)

    async def get_action_by_key(self, key: str) -> PendingActionRecord | None:
        result = await self.session.execute(
            select(PendingActionRecord).where(
                PendingActionRecord.idempotency_key == key
            )
        )
        return result.scalar_one_or_none()

    async def add_action(self, action: PendingActionRecord) -> None:
        self.session.add(action)
        await self.session.commit()
        await self.session.refresh(action)

    async def claim_action(self, action_id: UUID, now: datetime) -> bool:
        result = await self.session.execute(
            update(PendingActionRecord)
            .where(
                PendingActionRecord.id == action_id,
                PendingActionRecord.status == "prepared",
                PendingActionRecord.expires_at > now,
            )
            .values(status="processing")
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return cast(int, result.rowcount) == 1  # type: ignore[attr-defined]

    async def cancel_action(self, action_id: UUID, now: datetime) -> bool:
        result = await self.session.execute(
            update(PendingActionRecord)
            .where(
                PendingActionRecord.id == action_id,
                PendingActionRecord.status == "prepared",
                PendingActionRecord.expires_at > now,
            )
            .values(status="canceled")
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return cast(int, result.rowcount) == 1  # type: ignore[attr-defined]

    async def update_action_result(
        self,
        action_id: UUID,
        *,
        status: str,
        now: datetime,
        crm_record_id: str | None = None,
        response_json: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        await self.session.execute(
            update(PendingActionRecord)
            .where(
                PendingActionRecord.id == action_id,
                PendingActionRecord.status == "processing",
            )
            .values(
                status=status,
                confirmed_at=now if status == "confirmed" else None,
                crm_record_id=crm_record_id,
                response_json=response_json,
                error_code=error_code,
            )
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()

    async def add_audit(
        self,
        *,
        session_id: UUID,
        action_id: UUID | None,
        action: str,
        outcome: str,
        duration_ms: int = 0,
        crm_record_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            AuditLogRecord(
                session_id=session_id,
                action_id=action_id,
                action=action,
                outcome=outcome,
                duration_ms=max(0, duration_ms),
                crm_record_id=crm_record_id,
                details=details or {},
            )
        )
        await self.session.commit()


def as_utc(value: datetime) -> datetime:
    """Normalize SQLite's naive datetime results and preserve timezone-aware values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
