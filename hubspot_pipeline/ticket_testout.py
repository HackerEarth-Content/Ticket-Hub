"""
Exploratory script — inspect HubSpot ticket properties and distributions.

Prints:
  - All ticket pipelines and their stage names
  - Value distributions for: pipeline, stage, category, priority, resolution
  - Sample ticket subjects from the Support Pipeline

Usage:
    python -m ingestion.hubspot_pipeline.ticket_testout
    # or directly:
    python ingestion/hubspot_pipeline/ticket_testout.py

Requires HUBSPOT_API_KEY in .env
"""

from __future__ import annotations

import asyncio
import json
import os
from collections import Counter, defaultdict

import aiohttp
from dotenv import load_dotenv

load_dotenv()

HUBSPOT_API_KEY = os.environ.get("HUBSPOT_SERVICE_KEY", "")
BASE = "https://api.hubapi.com"

TICKET_PROPERTIES = [
    "subject",
    "hs_pipeline",
    "hs_pipeline_stage",
    "hs_ticket_category",
    "hs_ticket_priority",
    "hs_resolution",
    "hs_ticket_type",
    "createdate",
    "closed_date",  # NOT "closedate" -- that property doesn't exist in this portal
    "hs_lastmodifieddate",
    "hubspot_owner_id",
    "hs_time_to_first_response_sla_status",
    "hs_time_to_close_sla_status",
    "hs_last_csat_rating",
    "source_type",
]

# Max tickets to sample for distribution analysis (HubSpot page size max = 200)
SAMPLE_LIMIT = 500


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json",
    }


async def fetch_pipelines(session: aiohttp.ClientSession) -> dict[str, dict]:
    """Returns {pipeline_id: {label, stages: {stage_id: label}}}"""
    url = f"{BASE}/crm/v3/pipelines/tickets"
    async with session.get(url, headers=_headers()) as resp:
        resp.raise_for_status()
        data = await resp.json()

    pipelines: dict[str, dict] = {}
    for p in data.get("results", []):
        stages = {s["id"]: s["label"] for s in p.get("stages", [])}
        pipelines[p["id"]] = {"label": p["label"], "stages": stages}
    return pipelines


async def fetch_tickets_page(
    session: aiohttp.ClientSession,
    after: str | None = None,
    page_size: int = 200,
) -> tuple[list[dict], str | None]:
    """Fetch one page of tickets (all statuses, all pipelines). Returns (tickets, next_after)."""
    url = f"{BASE}/crm/v3/objects/tickets/search"
    body: dict = {
        "properties": TICKET_PROPERTIES,
        "limit": page_size,
        "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
    }
    if after:
        body["after"] = after

    async with session.post(url, headers=_headers(), json=body) as resp:
        resp.raise_for_status()
        data = await resp.json()

    tickets = data.get("results", [])
    next_after = data.get("paging", {}).get("next", {}).get("after")
    return tickets, next_after


async def sample_tickets(session: aiohttp.ClientSession, limit: int = SAMPLE_LIMIT) -> list[dict]:
    tickets: list[dict] = []
    after = None
    while len(tickets) < limit:
        page_size = min(200, limit - len(tickets))
        batch, after = await fetch_tickets_page(session, after=after, page_size=page_size)
        tickets.extend(batch)
        if not after:
            break
    return tickets


def _resolve(pipelines: dict[str, dict], pid: str, sid: str) -> tuple[str, str]:
    p_label = pipelines.get(pid, {}).get("label", pid or "—")
    s_label = pipelines.get(pid, {}).get("stages", {}).get(sid, sid or "—")
    return p_label, s_label


def _print_section(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def _print_counter(label: str, counter: Counter) -> None:
    print(f"\n  {label}:")
    for value, count in counter.most_common():
        print(f"    {count:>5}  {value}")


async def main() -> None:
    if not HUBSPOT_API_KEY:
        raise SystemExit("HUBSPOT_API_KEY not set in environment / .env")

    async with aiohttp.ClientSession() as session:
        # ── 1. Pipelines and stages ───────────────────────────────────────────
        _print_section("TICKET PIPELINES & STAGES")
        pipelines = await fetch_pipelines(session)
        for pid, p in pipelines.items():
            print(f"\n  Pipeline: {p['label']}  (id={pid})")
            for sid, s_label in p["stages"].items():
                print(f"    Stage: {s_label}  (id={sid})")

        # ── 2. Sample tickets ─────────────────────────────────────────────────
        _print_section(f"TICKET PROPERTY DISTRIBUTIONS  (sample ≤ {SAMPLE_LIMIT})")
        print("  Fetching tickets…", flush=True)
        tickets = await sample_tickets(session)
        print(f"  Fetched {len(tickets)} tickets.\n")

        # Build distributions
        pipeline_counter: Counter = Counter()
        stage_counter: Counter = Counter()
        category_counter: Counter = Counter()
        priority_counter: Counter = Counter()
        resolution_counter: Counter = Counter()
        type_counter: Counter = Counter()

        # Support Pipeline tickets → collect subjects for a quick look
        support_subjects: list[str] = []

        # Detect support pipeline id by label
        support_pipeline_id = next(
            (pid for pid, p in pipelines.items() if "support" in p["label"].lower()),
            None,
        )

        for t in tickets:
            props = t.get("properties", {})
            pid = props.get("hs_pipeline") or "—"
            sid = props.get("hs_pipeline_stage") or "—"
            p_label, s_label = _resolve(pipelines, pid, sid)

            pipeline_counter[p_label] += 1
            stage_counter[f"{p_label} / {s_label}"] += 1
            category_counter[props.get("hs_ticket_category") or "—"] += 1
            priority_counter[props.get("hs_ticket_priority") or "—"] += 1
            resolution_counter[props.get("hs_resolution") or "—"] += 1
            type_counter[props.get("hs_ticket_type") or "—"] += 1

            if support_pipeline_id and pid == support_pipeline_id:
                subj = props.get("subject") or "(no subject)"
                support_subjects.append(subj)

        _print_counter("Pipeline distribution", pipeline_counter)
        _print_counter("Pipeline / Stage distribution", stage_counter)
        _print_counter("Category (hs_ticket_category)", category_counter)
        _print_counter("Priority (hs_ticket_priority)", priority_counter)
        _print_counter("Resolution (hs_resolution)", resolution_counter)
        _print_counter("Type (hs_ticket_type)", type_counter)

        # ── 3. Support Pipeline subjects preview ──────────────────────────────
        if support_subjects:
            _print_section("SUPPORT PIPELINE — SAMPLE SUBJECTS (first 20)")
            for subj in support_subjects[:20]:
                print(f"  • {subj}")
        else:
            print("\n  (No Support Pipeline tickets found in sample — check pipeline label match)")

        # ── 4. Raw property keys for discovery ───────────────────────────────
        if tickets:
            _print_section("ALL PROPERTY KEYS SEEN ON TICKETS")
            all_keys = sorted({k for t in tickets for k in t.get("properties", {}).keys()})
            for k in all_keys:
                print(f"  {k}")


if __name__ == "__main__":
    asyncio.run(main())
