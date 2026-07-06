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

    # Auth (Google OAuth)
    USER_SECRET: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    FRONTEND_URL: str = "http://localhost:5173"
    API_BASE_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


settings = Settings()
