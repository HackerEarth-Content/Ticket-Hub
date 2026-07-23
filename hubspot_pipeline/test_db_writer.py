"""Self-check for the created_at floor filter: run `python hubspot_pipeline/test_db_writer.py`."""

from datetime import datetime, timedelta, timezone

from hubspot_pipeline.db_writer import _CREATED_FLOOR, _drop_pre_floor


def test_drop_pre_floor():
    before = {"ticket_id": "1", "created_at": _CREATED_FLOOR - timedelta(days=1)}
    at_floor = {"ticket_id": "2", "created_at": _CREATED_FLOOR}
    after = {"ticket_id": "3", "created_at": _CREATED_FLOOR + timedelta(days=1)}
    missing = {"ticket_id": "4", "created_at": None}

    kept = _drop_pre_floor([before, at_floor, after, missing])
    assert [r["ticket_id"] for r in kept] == ["2", "3", "4"]


if __name__ == "__main__":
    test_drop_pre_floor()
    print("All db_writer checks passed.")
