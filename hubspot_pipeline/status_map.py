"""Canonical ticket status lookup, collapsing per-pipeline stage IDs into
New / Open / Pending / Closing / Resolved.

Stage IDs are NOT shared across HubSpot pipelines (see handoff.md), so the
mapping is config (status_map.json), not hardcoded per-pipeline logic.
"""

from __future__ import annotations

import json
from pathlib import Path

_MAP_PATH = Path(__file__).parent / "status_map.json"

UNKNOWN_STATUS = "Unknown"


def _load() -> dict[str, dict[str, str]]:
    data = json.loads(_MAP_PATH.read_text())
    return {pid: p["stages"] for pid, p in data.get("pipelines", {}).items()}


_STAGE_TO_STATUS: dict[str, dict[str, str]] = _load()


def resolve_status(pipeline_id: str, stage_id: str) -> str:
    """Return the canonical status for a (pipeline_id, stage_id) pair."""
    return _STAGE_TO_STATUS.get(pipeline_id, {}).get(stage_id, UNKNOWN_STATUS)
