"""Application configuration — all values come from environment variables."""

import os


class Settings:
    app_name: str = "Opportunity Voice Assistant — Backend"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/voicecrm"
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
