"""Derived priority for the 78% of tickets with a blank hs_ticket_priority.

Rule order (first match wins), per handoff.md. Never overwrites the real
hs_ticket_priority -- the caller keeps both fields and an `inferred` flag.
"""

from __future__ import annotations

_URGENT_KEYWORDS = ("URGENT", "[P1]")
_HIGH_KEYWORDS = ("CRITICAL", "DOWN")

_HIGH_CATEGORIES = frozenset({
    "Test Loading Issues", "Unable to Login", "Login issues", "Webcam",
    "Audio/Video Issue", "IDE/Compiler", "Proctoring B2C",
})
_MEDIUM_CATEGORIES = frozenset({
    "Submission Related", "Test Access", "Dashboard Issues", "Result enquiry",
    "Team Management",
})
_LOW_CATEGORIES = frozenset({
    "Sales Enquiry", "Contest Info", "Registration Related", "Spam",
    "Not Actionable", "No Action Required",
})

# Stages where a bug is still open for triage -- floor priority at MEDIUM.
_BUG_PENDING_STAGES = frozenset({
    "Bugs pending on Backline/AE", "Bugs pending on QA/Platform",
})

_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "URGENT": 3}


def derive_priority(
    raw_priority: str | None,
    subject: str,
    categories: list[str],
    stage_label: str,
) -> tuple[str, bool]:
    """Return (priority, inferred). If raw_priority is set, it's returned as-is."""
    if raw_priority:
        return raw_priority, False

    subject_upper = subject.upper()
    if any(kw in subject_upper for kw in _URGENT_KEYWORDS):
        return "URGENT", True
    if any(kw in subject_upper for kw in _HIGH_KEYWORDS):
        return "HIGH", True

    candidate: str | None = None
    for cat in categories:
        if cat in _HIGH_CATEGORIES:
            candidate = "HIGH"
            break
        if cat in _MEDIUM_CATEGORIES and candidate is None:
            candidate = "MEDIUM"
        elif cat in _LOW_CATEGORIES and candidate is None:
            candidate = "LOW"

    if stage_label in _BUG_PENDING_STAGES:
        if candidate is None or _RANK[candidate] < _RANK["MEDIUM"]:
            candidate = "MEDIUM"

    return candidate or "MEDIUM", True
