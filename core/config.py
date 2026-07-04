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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


settings = Settings()
