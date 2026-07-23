"""Settings for the HubSpot dashboard extraction pipeline."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # HubSpot private-app token
    HUBSPOT_SERVICE_KEY: str

    DATABASE_URL: str

    OPENAI_API_KEY: str = ""

    # HubSpot search API allows up to 200 results per page
    TICKET_PAGE_SIZE: int = 200

    # Wootric NPS. Left blank means the NPS sync no-ops (see
    # wootric_pipeline.pipeline.run_incremental) rather than failing startup.
    WOOTRIC_CLIENT_ID: str = ""
    WOOTRIC_CLIENT_SECRET: str = ""
    WOOTRIC_API_BASE: str = "https://api.wootric.com"

    # Auth (Google OAuth)
    USER_SECRET: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    FRONTEND_URL: str
    API_BASE_URL: str
    ENVIRONMENT: str = "development"

    # Comma-separated Google account emails allowed to sign in. Empty means
    # anyone with a Google account can sign in (current/dev behavior).
    ALLOWED_EMAILS: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


settings = Settings()
