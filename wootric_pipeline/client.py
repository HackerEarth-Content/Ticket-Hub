"""Async Wootric API client -- OAuth client-credentials token + paginated
/v1/responses fetch, mirroring hubspot_pipeline.client's shape.
"""

from __future__ import annotations

from base64 import b64encode
from typing import AsyncIterator

import aiohttp

from core.config import settings

# Wootric's documented page-size cap.
_PER_PAGE = 50


def _basic_auth_header() -> str:
    raw = f"{settings.WOOTRIC_CLIENT_ID}:{settings.WOOTRIC_CLIENT_SECRET}".encode()
    return "Basic " + b64encode(raw).decode()


class WootricClient:
    def __init__(self) -> None:
        self._token: str | None = None

    async def _get_token(self, session: aiohttp.ClientSession) -> str:
        if self._token:
            return self._token
        url = f"{settings.WOOTRIC_API_BASE}/oauth/token"
        headers = {
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with session.post(url, headers=headers, data="grant_type=client_credentials") as resp:
            resp.raise_for_status()
            data = await resp.json()
        self._token = data["access_token"]
        return self._token

    async def fetch_responses(self, since_ts: int) -> AsyncIterator[dict]:
        """Yield raw NPS response dicts created at/after `since_ts` (unix seconds)."""
        async with aiohttp.ClientSession() as session:
            token = await self._get_token(session)
            headers = {"Authorization": f"Bearer {token}"}
            url = f"{settings.WOOTRIC_API_BASE}/v1/responses"
            page = 1
            while True:
                params = {"created[gte]": since_ts, "page": page, "per_page": _PER_PAGE}
                async with session.get(url, headers=headers, params=params) as resp:
                    resp.raise_for_status()
                    batch = await resp.json()

                if not batch:
                    return
                for raw in batch:
                    yield raw

                if len(batch) < _PER_PAGE:
                    return
                page += 1

    async def fetch_end_user(self, end_user_id: str) -> dict | None:
        """Best-effort: returns None if the end_user lookup fails, same
        fallback-not-failure approach as hubspot_pipeline.client.fetch_owners."""
        async with aiohttp.ClientSession() as session:
            token = await self._get_token(session)
            headers = {"Authorization": f"Bearer {token}"}
            url = f"{settings.WOOTRIC_API_BASE}/v1/end_users/{end_user_id}"
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
