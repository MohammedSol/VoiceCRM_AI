"""Application configuration — all values come from environment variables."""

import os


class Settings:
    app_name: str = "Opportunity Voice Assistant — Backend"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/voicecrm"
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    max_opportunity_amount: str = os.getenv("MAX_OPPORTUNITY_AMOUNT", "10000000")
    allowed_opportunity_stages: frozenset[str] = frozenset(
        value.strip()
        for value in os.getenv("SALESFORCE_ALLOWED_STAGES", "Qualification").split(",")
        if value.strip()
    )
    pending_action_ttl_seconds: int = int(
        os.getenv("PENDING_ACTION_TTL_SECONDS", "600")
    )
    crm_driver: str = os.getenv("CRM_DRIVER", "unconfigured").lower()


settings = Settings()
