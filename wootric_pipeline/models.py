"""Wootric NPS response data model."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


def _tag_name(tag: Any) -> str:
    return tag.get("name", str(tag)) if isinstance(tag, dict) else str(tag)


def _to_iso(value: Any) -> str:
    """Wootric's /v1/responses created_at comes back as an ISO string
    (verified live 2026-07-08) -- unlike the created[gte] query param, which
    takes unix seconds. Handles a raw unix timestamp too, in case that ever
    differs across API versions/plans."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()


class NpsSubmission(BaseModel):
    """A single Wootric NPS survey response, normalized for storage."""

    response_id: str
    end_user_id: str | None
    email: str | None
    score: int
    text: str | None
    completed: bool | None
    excluded_from_calculations: bool
    created_at: str  # ISO string
    tags: list[str]
    properties: dict[str, Any]

    @classmethod
    def from_raw(cls, raw: dict[str, Any], end_user: dict[str, Any] | None) -> "NpsSubmission":
        end_user = end_user or {}
        end_user_id = raw.get("end_user_id")
        properties = dict(end_user.get("properties") or {})
        if properties.get("company"):
            properties["company"] = html.unescape(properties["company"])
        return cls(
            response_id=str(raw["id"]),
            end_user_id=str(end_user_id) if end_user_id else None,
            email=end_user.get("email"),
            score=raw["score"],
            text=html.unescape(raw["text"]) if raw.get("text") else raw.get("text"),
            completed=raw.get("completed"),
            excluded_from_calculations=bool(raw.get("excluded_from_calculations")),
            created_at=_to_iso(raw["created_at"]),
            tags=[_tag_name(t) for t in (raw.get("tags") or [])],
            properties=properties,
        )
