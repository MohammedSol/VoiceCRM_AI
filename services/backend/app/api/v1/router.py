"""Session and confirmed opportunity workflow endpoints."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from voicecrm_contracts import CrmOpportunityDraft, CrmPort
from voicecrm_validation import validate_opportunity

from app.adapters.crm import CrmUnavailableError
from app.api.v1.dependencies import get_crm
from app.api.v1.schemas import (
    ConfirmActionResponse,
    CreateSessionResponse,
    PrepareActionRequest,
    PrepareActionResponse,
)
from app.core.config import settings
from app.db.session import get_db_session
from app.models.entities import PendingActionRecord
from app.repositories.workflow import WorkflowRepository, as_utc

router = APIRouter(prefix="/v1", tags=["workflow"])
logger = structlog.get_logger(__name__)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CrmDependency = Annotated[CrmPort, Depends(get_crm)]


@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(session: DbSession) -> CreateSessionResponse:
    repository = WorkflowRepository(session)
    record = await repository.create_session()
    logger.info(
        "session_created",
        session_id=str(record.id),
        operation="create_session",
        outcome="success",
    )
    return CreateSessionResponse(
        session_id=record.id, created_at=as_utc(record.created_at), status=record.status
    )


@router.post(
    "/sessions/{session_id}/actions/prepare",
    response_model=PrepareActionResponse,
    status_code=201,
)
async def prepare_action(
    session_id: UUID,
    body: PrepareActionRequest,
    session: DbSession,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=128)
    ],
) -> PrepareActionResponse:
    repository = WorkflowRepository(session)
    if await repository.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail={"code": "session_not_found"})

    try:
        max_amount = Decimal(settings.max_opportunity_amount)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=500, detail={"code": "invalid_amount_limit_configuration"}
        ) from exc
    if not max_amount.is_finite() or max_amount <= 0:
        raise HTTPException(
            status_code=500, detail={"code": "invalid_amount_limit_configuration"}
        )
    validated, issues = validate_opportunity(
        body.model_dump(),
        allowed_stages=settings.allowed_opportunity_stages,
        max_amount=max_amount,
    )
    if issues or validated is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_failed",
                "errors": [issue.__dict__ for issue in issues],
            },
        )

    payload = {
        "name": validated.name,
        "account_id": validated.account_id,
        "account_name": validated.account_name,
        "amount": format(validated.amount, "f"),
        "close_date": validated.close_date.isoformat(),
        "stage_name": validated.stage_name,
    }
    request_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    existing = await repository.get_action_by_key(idempotency_key)
    if existing is not None:
        return _replay_prepare(existing, session_id, request_hash)

    now = datetime.now(UTC)
    action = PendingActionRecord(
        session_id=session_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        payload=payload,
        expires_at=now + timedelta(seconds=settings.pending_action_ttl_seconds),
    )
    try:
        await repository.add_action(action)
    except IntegrityError:
        await session.rollback()
        existing = await repository.get_action_by_key(idempotency_key)
        if existing is None:
            raise HTTPException(
                status_code=409, detail={"code": "idempotency_conflict"}
            )
        return _replay_prepare(existing, session_id, request_hash)

    await repository.add_audit(
        session_id=session_id,
        action_id=action.id,
        action="prepare_opportunity",
        outcome="prepared",
        details={"kind": "opportunity_create"},
    )
    logger.info(
        "action_prepared",
        session_id=str(session_id),
        action_id=str(action.id),
        operation="prepare_opportunity",
        outcome="success",
    )
    return _prepare_response(action, replayed=False)


@router.post("/actions/{action_id}/confirm", response_model=ConfirmActionResponse)
async def confirm_action(
    action_id: UUID, session: DbSession, crm: CrmDependency
) -> ConfirmActionResponse:
    repository = WorkflowRepository(session)
    action = await repository.get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail={"code": "action_not_found"})
    if action.status == "confirmed" and action.crm_record_id:
        return ConfirmActionResponse(
            action_id=action.id,
            status="confirmed",
            crm_record_id=action.crm_record_id,
            replayed=True,
        )
    if action.status == "processing":
        raise HTTPException(status_code=409, detail={"code": "action_processing"})
    if action.status == "failed":
        raise HTTPException(status_code=409, detail={"code": "action_failed_no_retry"})
    if action.status == "canceled":
        raise HTTPException(status_code=409, detail={"code": "action_canceled"})
    if as_utc(action.expires_at) <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail={"code": "action_expired"})

    claimed = await repository.claim_action(action.id, datetime.now(UTC))
    if not claimed:
        raise HTTPException(status_code=409, detail={"code": "action_not_prepared"})

    started = time.perf_counter()
    try:
        draft = _crm_draft(action.payload)
        crm_record_id = await crm.create_opportunity(draft)
    except CrmUnavailableError:
        await _mark_failed(repository, action, "crm_unavailable", started)
        raise HTTPException(
            status_code=503, detail={"code": "crm_unavailable"}
        ) from None
    except Exception:
        await _mark_failed(repository, action, "crm_request_failed", started)
        raise HTTPException(
            status_code=502, detail={"code": "crm_request_failed"}
        ) from None

    response_json = {
        "action_id": str(action.id),
        "status": "confirmed",
        "crm_record_id": crm_record_id,
    }
    completed = datetime.now(UTC)
    await repository.update_action_result(
        action.id,
        status="confirmed",
        now=completed,
        crm_record_id=crm_record_id,
        response_json=response_json,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    await repository.add_audit(
        session_id=action.session_id,
        action_id=action.id,
        action="confirm_opportunity",
        outcome="confirmed",
        duration_ms=duration_ms,
        crm_record_id=crm_record_id,
        details={"kind": "opportunity_create"},
    )
    logger.info(
        "action_confirmed",
        session_id=str(action.session_id),
        action_id=str(action.id),
        operation="confirm_opportunity",
        outcome="success",
        duration_ms=duration_ms,
        crm_record_id=crm_record_id,
    )
    return ConfirmActionResponse(
        action_id=action.id,
        status="confirmed",
        crm_record_id=crm_record_id,
    )


@router.post("/actions/{action_id}/cancel", status_code=204)
async def cancel_action(action_id: UUID, session: DbSession) -> None:
    repository = WorkflowRepository(session)
    action = await repository.get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail={"code": "action_not_found"})
    if as_utc(action.expires_at) <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail={"code": "action_expired"})
    if not await repository.cancel_action(action_id, datetime.now(UTC)):
        raise HTTPException(status_code=409, detail={"code": "action_not_prepared"})
    await repository.add_audit(
        session_id=action.session_id,
        action_id=action.id,
        action="cancel_opportunity",
        outcome="canceled",
        details={"kind": "opportunity_create"},
    )
    logger.info(
        "action_canceled",
        session_id=str(action.session_id),
        action_id=str(action.id),
        operation="cancel_opportunity",
        outcome="success",
    )


def _replay_prepare(
    action: PendingActionRecord, session_id: UUID, request_hash: str
) -> PrepareActionResponse:
    if action.session_id != session_id or action.request_hash != request_hash:
        raise HTTPException(status_code=409, detail={"code": "idempotency_conflict"})
    if as_utc(action.expires_at) <= datetime.now(UTC) and action.status == "prepared":
        raise HTTPException(status_code=410, detail={"code": "action_expired"})
    return _prepare_response(action, replayed=True)


def _prepare_response(
    action: PendingActionRecord, *, replayed: bool
) -> PrepareActionResponse:
    return PrepareActionResponse(
        action_id=action.id,
        session_id=action.session_id,
        status=action.status,
        expires_at=as_utc(action.expires_at),
        confirmation_summary={
            "name": str(action.payload["name"]),
            "account_name": str(action.payload["account_name"]),
            "amount": str(action.payload["amount"]),
            "close_date": str(action.payload["close_date"]),
            "stage_name": str(action.payload["stage_name"]),
        },
        replayed=replayed,
    )


def _crm_draft(payload: dict[str, Any]) -> CrmOpportunityDraft:
    return CrmOpportunityDraft(
        name=str(payload["name"]),
        account_id=str(payload["account_id"]),
        account_name=str(payload["account_name"]),
        amount=Decimal(str(payload["amount"])),
        close_date=datetime.fromisoformat(str(payload["close_date"])).date(),
        stage_name=str(payload["stage_name"]),
    )


async def _mark_failed(
    repository: WorkflowRepository,
    action: PendingActionRecord,
    error_code: str,
    started: float,
) -> None:
    duration_ms = int((time.perf_counter() - started) * 1000)
    await repository.update_action_result(
        action.id, status="failed", now=datetime.now(UTC), error_code=error_code
    )
    await repository.add_audit(
        session_id=action.session_id,
        action_id=action.id,
        action="confirm_opportunity",
        outcome="failed",
        duration_ms=duration_ms,
        details={"error_code": error_code, "kind": "opportunity_create"},
    )
    logger.warning(
        "action_confirmation_failed",
        session_id=str(action.session_id),
        action_id=str(action.id),
        operation="confirm_opportunity",
        outcome="failure",
        duration_ms=duration_ms,
        error_code=error_code,
    )
