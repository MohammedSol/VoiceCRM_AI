"""Pure, deterministic business validation rules."""

from voicecrm_validation.opportunity import (
    ValidatedOpportunity,
    ValidationIssue,
    validate_opportunity,
)

__all__ = ["ValidatedOpportunity", "ValidationIssue", "validate_opportunity"]
