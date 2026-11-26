"""Validation for opportunity drafts; this module has no I/O or framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    code: str
    message: str


@dataclass(frozen=True)
class ValidatedOpportunity:
    name: str
    account_id: str
    account_name: str
    amount: Decimal
    close_date: date
    stage_name: str


_MAX_NAME_LENGTH = 120
_MAX_ACCOUNT_ID_LENGTH = 80
_MAX_ACCOUNT_NAME_LENGTH = 255


def validate_opportunity(
    data: dict[str, Any],
    *,
    allowed_stages: frozenset[str],
    max_amount: Decimal,
    today: date | None = None,
) -> tuple[ValidatedOpportunity | None, list[ValidationIssue]]:
    """Validate untrusted input and return stable field-level issue codes."""
    issues: list[ValidationIssue] = []
    if not max_amount.is_finite() or max_amount <= 0:
        raise ValueError("max_amount must be a positive finite Decimal")
    name = _required_text(data.get("name"), "name", issues, _MAX_NAME_LENGTH)
    account_id = _required_text(
        data.get("account_id"), "account_id", issues, _MAX_ACCOUNT_ID_LENGTH
    )
    account_name = _required_text(
        data.get("account_name"), "account_name", issues, _MAX_ACCOUNT_NAME_LENGTH
    )

    amount_value = data.get("amount")
    amount: Decimal | None = None
    if isinstance(amount_value, bool) or amount_value is None:
        issues.append(ValidationIssue("amount", "required", "Amount is required."))
    else:
        try:
            amount = Decimal(str(amount_value).strip())
        except (InvalidOperation, ValueError, AttributeError):
            issues.append(
                ValidationIssue("amount", "invalid_decimal", "Enter a valid amount.")
            )
        else:
            if not amount.is_finite():
                issues.append(
                    ValidationIssue(
                        "amount", "invalid_decimal", "Enter a valid amount."
                    )
                )
                amount = None
            elif amount <= 0:
                issues.append(
                    ValidationIssue(
                        "amount",
                        "must_be_positive",
                        "Amount must be greater than zero.",
                    )
                )
            elif amount > max_amount:
                issues.append(
                    ValidationIssue(
                        "amount",
                        "exceeds_limit",
                        "Amount exceeds the configured limit.",
                    )
                )

    close_date_value = data.get("close_date")
    close_date: date | None = None
    if type(close_date_value) is date:
        close_date = close_date_value
    elif isinstance(close_date_value, str):
        try:
            close_date = date.fromisoformat(close_date_value)
        except ValueError:
            pass
    if close_date is None:
        issues.append(
            ValidationIssue(
                "close_date", "invalid_date", "Use a valid YYYY-MM-DD date."
            )
        )
    elif close_date < (today or date.today()):
        issues.append(
            ValidationIssue(
                "close_date", "date_in_past", "Close date cannot be in the past."
            )
        )

    stage_value = data.get("stage_name")
    stage_name = stage_value.strip() if isinstance(stage_value, str) else ""
    if not stage_name:
        issues.append(
            ValidationIssue("stage_name", "required", "Stage name is required.")
        )
    elif stage_name not in allowed_stages:
        issues.append(
            ValidationIssue("stage_name", "unknown_stage", "Stage is not allowed.")
        )

    if (
        issues
        or name is None
        or account_id is None
        or account_name is None
        or amount is None
        or close_date is None
    ):
        return None, issues
    return (
        ValidatedOpportunity(
            name=name,
            account_id=account_id,
            account_name=account_name,
            amount=amount,
            close_date=close_date,
            stage_name=stage_name,
        ),
        [],
    )


def _required_text(
    value: Any, field: str, issues: list[ValidationIssue], max_length: int
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue(field, "required", f"{field} is required."))
        return None
    result = value.strip()
    if len(result) > max_length:
        issues.append(ValidationIssue(field, "too_long", f"{field} is too long."))
        return None
    return result
