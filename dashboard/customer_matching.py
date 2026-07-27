"""Best-effort matching of a free-text company-name list against ticket
customer_name values (already Blackops-resolved, see
hubspot_pipeline/customer_map.py). There's no canonical alias table for
this -- exact string matching would miss common aliasing in this data (e.g.
"Entri India" vs "Entri", "Modmed (Tech)" and "Modmed (Non Tech)" both
being "Modmed") -- so this normalizes and falls back to fuzzy matching.
Known limitation: names with zero token overlap with their real Blackops
name (e.g. an account renamed entirely) won't match; those fall through to
the caller's "no tickets found" bucket even if tickets exist.
"""

from __future__ import annotations

import difflib
import re

_PARENS_RE = re.compile(r"\([^)]*\)")
_STOPWORDS = {
    "india", "pvt", "ltd", "private", "limited", "llp", "inc",
    "incorporated", "technologies", "technology", "account",
}
_FUZZY_CUTOFF = 0.75
_MIN_SUBSTRING_LEN = 4


def normalize_name(name: str) -> str:
    name = _PARENS_RE.sub(" ", name)
    tokens = [t for t in re.findall(r"[a-z0-9]+", name.lower()) if t not in _STOPWORDS]
    return " ".join(tokens)


def match_names(
    input_names: list[str], ticket_names: list[str]
) -> tuple[dict[str, list[str]], list[str]]:
    """Returns (blackops_name -> list of input names that matched it,
    input names that matched nothing)."""
    normalized_tickets = {t: normalize_name(t) for t in ticket_names}
    matched: dict[str, list[str]] = {}
    unmatched: list[str] = []

    for input_name in input_names:
        norm_input = normalize_name(input_name)
        if not norm_input:
            unmatched.append(input_name)
            continue

        best_ticket = None
        for ticket_name, norm_ticket in normalized_tickets.items():
            if norm_input == norm_ticket:
                best_ticket = ticket_name
                break
            if (
                len(norm_input) >= _MIN_SUBSTRING_LEN
                and len(norm_ticket) >= _MIN_SUBSTRING_LEN
                and (norm_input in norm_ticket or norm_ticket in norm_input)
            ):
                best_ticket = ticket_name
                break

        if best_ticket is None:
            close = difflib.get_close_matches(
                norm_input, list(normalized_tickets.values()), n=1, cutoff=_FUZZY_CUTOFF
            )
            if close:
                best_ticket = next(t for t, n in normalized_tickets.items() if n == close[0])

        if best_ticket is not None:
            matched.setdefault(best_ticket, []).append(input_name)
        else:
            unmatched.append(input_name)

    return matched, unmatched
