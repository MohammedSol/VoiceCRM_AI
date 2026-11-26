"""Structured JSON logging with an allowlist of safe event fields."""

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

_SAFE_FIELDS = frozenset(
    {
        "request_id",
        "session_id",
        "action_id",
        "operation",
        "outcome",
        "duration_ms",
        "error_code",
        "crm_record_id",
    }
)


def _allowlisted_fields(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    del logger, method_name
    event = event_dict.get("event", "event")
    safe = {key: value for key, value in event_dict.items() if key in _SAFE_FIELDS}
    safe["event"] = event
    return safe


def configure_logging(log_level: str) -> None:
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), force=True)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            _allowlisted_fields,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
