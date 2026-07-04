"""Category normalization for the dashboard's module/category distribution chart.

hs_ticket_category is a semicolon-joined multi-select free-text field
(e.g. "Test Access;Proctoring B2C") -- must be split before counting, or a
pie chart shows ~70 tiny slices. Module grouping is config
(category_taxonomy.json), not hardcoded, per handoff.md.
"""

from __future__ import annotations

import json
from pathlib import Path

_TAXONOMY_PATH = Path(__file__).parent / "category_taxonomy.json"

OTHER_MODULE = "Other"
UNCATEGORIZED_MODULE = "Uncategorized"


def _load() -> tuple[dict[str, str], dict[str, str]]:
    data = json.loads(_TAXONOMY_PATH.read_text())
    category_to_module: dict[str, str] = {}
    for module, categories in data.get("modules", {}).items():
        for cat in categories:
            category_to_module[cat] = module
    return category_to_module, data.get("typo_map", {})


_CATEGORY_TO_MODULE, _TYPO_MAP = _load()


def split_categories(raw_category: str | None) -> list[str]:
    """Split a semicolon-joined category string, normalising known typos."""
    if not raw_category:
        return []
    parts = [p.strip() for p in raw_category.split(";") if p.strip()]
    return [_TYPO_MAP.get(p, p) for p in parts]


def resolve_module(categories: list[str]) -> str:
    """Return the module for a ticket's categories (first match wins)."""
    if not categories:
        return UNCATEGORIZED_MODULE
    for cat in categories:
        module = _CATEGORY_TO_MODULE.get(cat)
        if module:
            return module
    return OTHER_MODULE
