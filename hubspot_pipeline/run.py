"""CLI entry point for the HubSpot dashboard extraction pipeline.

Usage:
    python -m hubspot_pipeline.run --days 7
    python -m hubspot_pipeline.run --days 30 --out tickets.jsonl
    python -m hubspot_pipeline.run --full   # since _FULL_PULL_FLOOR

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
from datetime import datetime, timezone
from pathlib import Path

from core.database import db_manager
from hubspot_pipeline import db_writer, pipeline
from wootric_pipeline import db_writer as wootric_db_writer
from wootric_pipeline import pipeline as wootric_pipeline

# Floor for --full -- NOT HubSpot account creation. Tickets before this date
# were intentionally deleted from the DB (2026-07-07); a --full pull that
# reached back further would just re-fetch and re-insert them.
_FULL_PULL_FLOOR = datetime(2026, 2, 2, tzinfo=timezone.utc)


async def _main(
    since_ms: int, out: str | None, write_db: bool, incremental: bool
) -> None:
    if incremental:
        await db_manager.initialize()
        ticket_stats = await pipeline.run_incremental()
        csat_stats = await pipeline.run_csat_incremental()
        nps_stats = await wootric_pipeline.run_incremental()
        await db_manager.close()
        print(
            json.dumps(
                {"tickets": ticket_stats, "csat": csat_stats, "nps": nps_stats},
                indent=2,
            )
        )
        return

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
        nps_submissions = await wootric_pipeline.extract(since_ms // 1000)
        await wootric_db_writer.upsert_nps_responses(nps_submissions)
        await db_manager.close()
        print(
            f"Upserted {len(tickets)} ticket(s), {len(csat_submissions)} CSAT response(s), "
            f"and {len(nps_submissions)} NPS response(s) into the database"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HubSpot dashboard extraction pipeline"
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Look back N days (default: 30)"
    )
    parser.add_argument("--full", action="store_true", help="Full historical pull")
    parser.add_argument(
        "--out", type=str, default=None, help="Optional JSONL output path"
    )
    parser.add_argument(
        "--write-db", action="store_true", help="Upsert results into the tickets table"
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Sync from the last cursor and advance it (for scheduled runs)",
    )
    args = parser.parse_args()

    if args.full:
        since_ms = int(_FULL_PULL_FLOOR.timestamp() * 1000)
    else:
        since_ms = int((time.time() - args.days * 86400) * 1000)

    asyncio.run(
        _main(
            since_ms=since_ms,
            out=args.out,
            write_db=args.write_db,
            incremental=args.incremental,
        )
    )


if __name__ == "__main__":
    main()
