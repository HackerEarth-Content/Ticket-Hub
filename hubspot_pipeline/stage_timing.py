"""Per-stage entry/exit/cumulative-time tracking for the 4 Support Pipeline
stages where backline escalation happens. Keyed by a short stage_key (not the
raw HubSpot stage_id) so JSONB storage and API responses are self-explanatory.

Stage IDs verified live against this portal on 2026-07-04.
"""

from __future__ import annotations

STAGE_TIMING_STAGES: dict[str, dict[str, str]] = {
    "backline_ae": {"stage_id": "1114226809", "label": "Bugs pending on Backline/AE"},
    "be_ae": {"stage_id": "1208415673", "label": "Pending on BE/AE"},
    "qa_platform": {"stage_id": "1289560323", "label": "Bugs pending on QA/Platform"},
    "engineering": {"stage_id": "70862658", "label": "Pending on Engineering"},
}

# The two parallel entry points into backline -- a ticket enters one or the
# other, never both, so "path" is which door it came through.
_BUG_BOUNTY_PATH_KEY = "backline_ae"
_FRONTLINE_ESCALATION_PATH_KEY = "be_ae"

BUG_BOUNTY_PATH = "Bug Bounty"
FRONTLINE_ESCALATION_PATH = "Frontline Escalation"


def resolve_backline_path(stage_timings: dict[str, dict]) -> str | None:
    """Which backline entry point a ticket came through, or None if it never
    reached backline at all."""
    if stage_timings.get(_BUG_BOUNTY_PATH_KEY, {}).get("entered_at"):
        return BUG_BOUNTY_PATH
    if stage_timings.get(_FRONTLINE_ESCALATION_PATH_KEY, {}).get("entered_at"):
        return FRONTLINE_ESCALATION_PATH
    return None
