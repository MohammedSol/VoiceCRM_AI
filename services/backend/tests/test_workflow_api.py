from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.core import config

VALID_DRAFT = {
    "name": "Confidential Deal Name",
    "account_id": "001000000000001AAA",
    "account_name": "Confidential Account Name",
    "amount": "12345.67",
    "close_date": "2027-03-31",
    "stage_name": "Qualification",
}


def create_session(client: TestClient) -> str:
    response = client.post("/v1/sessions")
    assert response.status_code == 201
    return response.json()["session_id"]


def prepare(client: TestClient, session_id: str, key: str = "test-key-0001"):
    return client.post(
        f"/v1/sessions/{session_id}/actions/prepare",
        headers={"Idempotency-Key": key},
        json=VALID_DRAFT,
    )


def test_prepare_confirm_and_replay_creates_once(api_client) -> None:
    client, crm = api_client
    session_id = create_session(client)
    prepared = prepare(client, session_id)
    assert prepared.status_code == 201
    assert prepared.json()["status"] == "prepared"
    assert prepared.json()["confirmation_summary"]["amount"] == "12345.67"

    action_id = prepared.json()["action_id"]
    first = client.post(f"/v1/actions/{action_id}/confirm")
    second = client.post(f"/v1/actions/{action_id}/confirm")

    assert first.status_code == 200
    assert first.json()["status"] == "confirmed"
    assert second.status_code == 200
    assert second.json()["replayed"] is True
    assert first.json()["crm_record_id"] == second.json()["crm_record_id"]
    assert len(crm.created) == 1


def test_concurrent_confirms_make_at_most_one_crm_call(api_client) -> None:
    client, crm = api_client
    session_id = create_session(client)
    action_id = prepare(client, session_id).json()["action_id"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: client.post(f"/v1/actions/{action_id}/confirm"), range(2)
            )
        )

    assert all(response.status_code in {200, 409} for response in responses)
    assert any(response.status_code == 200 for response in responses)
    assert len(crm.created) == 1


def test_validation_rejects_bad_amount_before_persisting(api_client) -> None:
    client, crm = api_client
    session_id = create_session(client)
    invalid = {**VALID_DRAFT, "amount": "not-money"}
    response = client.post(
        f"/v1/sessions/{session_id}/actions/prepare",
        headers={"Idempotency-Key": "test-key-0002"},
        json=invalid,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["code"] == "invalid_decimal"
    assert crm.created == []


def test_confirm_without_prepare_is_rejected(api_client) -> None:
    client, crm = api_client
    response = client.post("/v1/actions/00000000-0000-0000-0000-000000000001/confirm")
    assert response.status_code == 404
    assert crm.created == []


def test_cancel_prevents_confirmation(api_client) -> None:
    client, crm = api_client
    session_id = create_session(client)
    action_id = prepare(client, session_id).json()["action_id"]

    canceled = client.post(f"/v1/actions/{action_id}/cancel")
    confirmed = client.post(f"/v1/actions/{action_id}/confirm")

    assert canceled.status_code == 204
    assert confirmed.status_code == 409
    assert confirmed.json()["detail"]["code"] == "action_canceled"
    assert crm.created == []


def test_expired_pending_action_is_rejected(api_client, monkeypatch) -> None:
    client, crm = api_client
    session_id = create_session(client)
    monkeypatch.setattr(config.settings, "pending_action_ttl_seconds", 0)
    action_id = prepare(client, session_id, "test-key-expire").json()["action_id"]

    response = client.post(f"/v1/actions/{action_id}/confirm")
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "action_expired"
    assert crm.created == []


def test_prepare_idempotency_conflict_rejects_different_payload(api_client) -> None:
    client, _ = api_client
    session_id = create_session(client)
    first = prepare(client, session_id, "test-key-same-01")
    different = {**VALID_DRAFT, "amount": "999.00"}
    replay = client.post(
        f"/v1/sessions/{session_id}/actions/prepare",
        headers={"Idempotency-Key": "test-key-same-01"},
        json=different,
    )
    assert first.status_code == 201
    assert replay.status_code == 409
    assert replay.json()["detail"]["code"] == "idempotency_conflict"


def test_structured_logs_never_include_opportunity_values(api_client, caplog) -> None:
    client, _ = api_client
    session_id = create_session(client)
    with caplog.at_level(logging.INFO):
        response = prepare(client, session_id, "test-key-log-0001")
    assert response.status_code == 201
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert "Confidential Deal Name" not in rendered
    assert "Confidential Account Name" not in rendered
    assert "12345.67" not in rendered
    assert (
        json.loads(
            next(line for line in rendered.splitlines() if "action_prepared" in line)
        )["outcome"]
        == "success"
    )
