"""CLI entry point for the HubSpot dashboard extraction pipeline.

Usage:
    python -m hubspot_pipeline.run --days 7
    python -m hubspot_pipeline.run --days 30 --out tickets.jsonl
    python -m hubspot_pipeline.run --full   # since HubSpot account creation

    # Incremental sync (what the scheduled/cron job should call) --
    # picks up from the last cursor, writes to the DB, advances the cursor.
    python -m hubspot_pipeline.run --incremental


    date ranges and source as a filter
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from core.database import db_manager
from hubspot_pipeline import db_writer, pipeline

# Fallback lookback for --full; HubSpot doesn't expose an "account created"
# API, so this just needs to predate the oldest ticket.
_FULL_PULL_DAYS = 3650


async def _main(days: int, out: str | None, write_db: bool, incremental: bool) -> None:
    if incremental:
        await db_manager.initialize()
        ticket_stats = await pipeline.run_incremental()
        csat_stats = await pipeline.run_csat_incremental()
        await db_manager.close()
        print(json.dumps({"tickets": ticket_stats, "csat": csat_stats}, indent=2))
        return

    since_ms = int((time.time() - days * 86400) * 1000)
    tickets = await pipeline.extract(since_ms)
    stats = pipeline.summarize(tickets)
    print(json.dumps(stats, indent=2))

    if out:
        pipeline.write_jsonl(tickets, Path(out))
        print(f"Wrote {len(tickets)} ticket(s) to {out}")

    if write_db:
        await db_manager.initialize()
        await db_writer.upsert_tickets(tickets)
        # CSAT matching reads ticket owner/closed_at from the DB, so this
        # must run after the ticket upsert above.
        csat_submissions = await pipeline.extract_csat(since_ms)
        await db_writer.upsert_csat_responses(csat_submissions)
        await db_manager.close()
        print(
            f"Upserted {len(tickets)} ticket(s) and {len(csat_submissions)} "
            "CSAT response(s) into the database"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="HubSpot dashboard extraction pipeline")
    parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    parser.add_argument("--full", action="store_true", help="Full historical pull")
    parser.add_argument("--out", type=str, default=None, help="Optional JSONL output path")
    parser.add_argument(
        "--write-db", action="store_true", help="Upsert results into the tickets table"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Sync from the last cursor and advance it (for scheduled runs)",
    )
    args = parser.parse_args()

    days = _FULL_PULL_DAYS if args.full else args.days
    asyncio.run(_main(days=days, out=args.out, write_db=args.write_db, incremental=args.incremental))


if __name__ == "__main__":
    main()
