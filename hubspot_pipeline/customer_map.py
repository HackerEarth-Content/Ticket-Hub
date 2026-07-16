"""Ticket -> customer/account name, for the per-customer volume and status
breakdown KPIs. HubSpot exposes 3 separate properties for this depending on
how the ticket was created -- verified live 2026-07-06, ~4% combined
coverage across Support Pipeline (most tickets are individual
candidates/hackathon participants, not tied to any account)."""

from __future__ import annotations

# hs_primary_company_name resolves to HackerEarth's own CRM company record
# (id 748031095) on a large share of tickets -- verified live 2026-07-06,
# it was the single most common value in a 100-ticket sample. That's HubSpot's
# automatic association picking up the company itself, not a customer, so it
# never counts as one here. blackops_account_name (manually chosen by the
# agent per ticket) never has this problem.
_INTERNAL_NAMES = frozenset({"hackerearth"})

# blackops_account_name's dropdown includes a literal "Others" option --
# picked when the real account isn't in the dropdown list, with the actual
# name typed into other_blackops_account_name instead. Verified live
# 2026-07-09: every "Others"-dropdown ticket sampled had a real company name
# in other_blackops_account_name (e.g. "Photon", "Totum7"), so treating
# "Others" as truthy silently discarded it.
_BLACKOPS_OTHERS_VALUE = "others"


def resolve_customer_name(props: dict) -> str | None:
    """blackops_account_name (dropdown) -> other_blackops_account_name
    (free-text fallback when not in the dropdown, or when the dropdown value
    is the "Others" placeholder) -> hs_primary_company_name (native HubSpot
    company association). Different sources can spell the same account
    differently (e.g. "Loyalty Juggernaut Inc" vs "...India") -- no
    fuzzy-matching dedup here, that's a known limitation, not a bug."""
    blackops_name = props.get("blackops_account_name")
    if blackops_name and blackops_name.strip().casefold() == _BLACKOPS_OTHERS_VALUE:
        blackops_name = None

    name = (
        blackops_name
        or props.get("other_blackops_account_name")
        or props.get("hs_primary_company_name")
        or None
    )
    if name and name.strip().casefold() in _INTERNAL_NAMES:
        return None
    return name
