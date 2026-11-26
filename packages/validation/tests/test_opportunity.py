from datetime import date, timedelta
from decimal import Decimal

import pytest
from voicecrm_validation import validate_opportunity

TODAY = date(2026, 11, 25)
BASE = {
    "name": "Pilot opportunity",
    "account_id": "001000000000001AAA",
    "account_name": "Acme Test",
    "amount": "10000.25",
    "close_date": (TODAY + timedelta(days=30)).isoformat(),
    "stage_name": "Qualification",
}
STAGES = frozenset({"Qualification"})


def validate(data: dict[str, object]):
    return validate_opportunity(
        data,
        allowed_stages=STAGES,
        max_amount=Decimal(100000),
        today=TODAY,
    )


def test_valid_draft_returns_decimal_without_float_conversion() -> None:
    result, errors = validate(BASE)
    assert errors == []
    assert result is not None
    assert result.amount == Decimal("10000.25")


@pytest.mark.parametrize(
    ("field", "value", "error_code"),
    [
        ("amount", "not a number", "invalid_decimal"),
        ("amount", "-1", "must_be_positive"),
        ("amount", "100001", "exceeds_limit"),
        ("close_date", "2026-11-24", "date_in_past"),
        ("close_date", "not-a-date", "invalid_date"),
        ("stage_name", "Unknown", "unknown_stage"),
        ("name", "   ", "required"),
        ("account_id", None, "required"),
        ("account_name", "", "required"),
    ],
)
def test_invalid_fields_return_stable_codes(
    field: str, value: object, error_code: str
) -> None:
    draft = {**BASE, field: value}
    result, errors = validate(draft)
    assert result is None
    assert error_code in {error.code for error in errors}
