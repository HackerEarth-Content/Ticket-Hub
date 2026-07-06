"""final_resolution -> ownership bucket, for the resolution-ownership/
dependency-distribution KPI (who actually resolves tickets: frontline
support, engineering, backline, automation, or nobody).

Bucket grouping is config (resolution_taxonomy.json), not hardcoded, same
pattern as category_map.py.
"""

from __future__ import annotations

import json
from pathlib import Path

_TAXONOMY_PATH = Path(__file__).parent / "resolution_taxonomy.json"

UNRESOLVED_BUCKET = "Unresolved"
OTHER_BUCKET = "Other"

# A ticket is actionable unless explicitly marked no-action -- a blank
# final_resolution (not yet resolved) still counts as actionable.
_NON_ACTIONABLE_RESOLUTIONS = frozenset({"No Action Taken"})


def _load() -> dict[str, str]:
    data = json.loads(_TAXONOMY_PATH.read_text())
    return {
        value: bucket
        for bucket, values in data.get("buckets", {}).items()
        for value in values
    }


_RESOLUTION_TO_BUCKET: dict[str, str] = _load()


def resolve_resolution_bucket(final_resolution: str | None) -> str:
    """Return the ownership bucket for a ticket's final_resolution."""
    if not final_resolution:
        return UNRESOLVED_BUCKET
    return _RESOLUTION_TO_BUCKET.get(final_resolution, OTHER_BUCKET)


def is_actionable(final_resolution: str | None) -> bool:
    return final_resolution not in _NON_ACTIONABLE_RESOLUTIONS
