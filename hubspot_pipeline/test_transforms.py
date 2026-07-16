"""Self-check for the transform logic: run `python hubspot_pipeline/test_transforms.py`."""

from datetime import datetime, timedelta, timezone

from hubspot_pipeline.category_map import resolve_module, split_categories
from hubspot_pipeline.customer_map import resolve_customer_name
from hubspot_pipeline.models import _extract_channel, _ms_to_hours, _sla_met, _to_bool
from hubspot_pipeline.pipeline import _match_ticket
from hubspot_pipeline.priority import derive_priority
from hubspot_pipeline.resolution_map import is_actionable, resolve_resolution_bucket
from hubspot_pipeline.stage_timing import resolve_backline_path
from hubspot_pipeline.status_map import resolve_status


def test_split_categories():
    assert split_categories("Test Access;Proctoring B2C;Result enquiry") == [
        "Test Access", "Proctoring B2C", "Result enquiry",
    ]
    assert split_categories("Campatibility") == ["Compatibility"]  # typo fixed
    assert split_categories(None) == []
    assert split_categories("") == []


def test_resolve_module():
    assert resolve_module(["Webcam"]) == "Proctoring"
    assert resolve_module(["Spam"]) == "Non-Actionable"
    assert resolve_module(["Some Unmapped Category"]) == "Other"
    assert resolve_module([]) == "Uncategorized"


def test_resolve_status():
    assert resolve_status("0", "54413370") == "Resolved"  # Support / Closed
    assert resolve_status("0", "54370401") == "New"        # Support / New
    assert resolve_status("0", "nonexistent-stage") == "Unknown"
    assert resolve_status("nonexistent-pipeline", "1") == "Unknown"


def test_derive_priority():
    # Real priority is never overwritten.
    assert derive_priority("HIGH", "anything", [], "Open") == ("HIGH", False)
    # Subject keyword wins first.
    assert derive_priority(None, "[URGENT] site is down", [], "Open") == ("URGENT", True)
    assert derive_priority(None, "Production is DOWN", [], "Open") == ("HIGH", True)
    # Category-based default.
    assert derive_priority(None, "hello", ["Webcam"], "Open") == ("HIGH", True)
    assert derive_priority(None, "hello", ["Spam"], "Open") == ("LOW", True)
    # Bug-pending stage floors LOW/None up to MEDIUM but doesn't downgrade HIGH.
    assert derive_priority(None, "hello", ["Spam"], "Bugs pending on Backline/AE") == ("MEDIUM", True)
    assert derive_priority(None, "hello", ["Webcam"], "Bugs pending on Backline/AE") == ("HIGH", True)
    # Fallback.
    assert derive_priority(None, "hello", [], "Open") == ("MEDIUM", True)


def test_resolve_resolution_bucket():
    assert resolve_resolution_bucket("Issue Resolved") == "Support"
    assert resolve_resolution_bucket("Issue Resolved Engineering") == "Engineering"
    assert resolve_resolution_bucket("Closed by Automation") == "Automation"
    assert resolve_resolution_bucket("No Action Taken") == "Non-Actionable"
    assert resolve_resolution_bucket("Some New Value HubSpot Adds Later") == "Other"
    assert resolve_resolution_bucket(None) == "Unresolved"
    assert resolve_resolution_bucket("") == "Unresolved"


def test_is_actionable():
    assert is_actionable(None) is True          # not yet resolved -- still actionable
    assert is_actionable("Issue Resolved") is True
    assert is_actionable("No Action Taken") is False


def test_resolve_backline_path():
    assert resolve_backline_path({"backline_ae": {"entered_at": "2026-01-01T00:00:00Z"}}) == "Bug Bounty"
    assert resolve_backline_path({"be_ae": {"entered_at": "2026-01-01T00:00:00Z"}}) == "Frontline Escalation"
    assert resolve_backline_path({}) is None
    assert resolve_backline_path({"backline_ae": {"entered_at": None}}) is None


def test_ms_to_hours():
    assert _ms_to_hours("3600000") == 1.0
    assert _ms_to_hours("1800000") == 0.5
    assert _ms_to_hours(None) is None
    assert _ms_to_hours("") is None


def test_to_bool():
    assert _to_bool("true") is True
    assert _to_bool("false") is False
    assert _to_bool(None) is None
    assert _to_bool("") is None


def test_sla_met():
    # sla_percentage is misleadingly named -- it's actually a 0/1 met-flag.
    assert _sla_met("1") is True
    assert _sla_met("0") is False
    assert _sla_met(None) is None
    assert _sla_met("") is None


def test_resolve_customer_name():
    # "Others" dropdown value -> falls through to the free-text field.
    assert resolve_customer_name({"blackops_account_name": "Others", "other_blackops_account_name": "Photon"}) == "Photon"
    assert resolve_customer_name({"blackops_account_name": "others"}) is None  # no fallback available
    # Real dropdown value wins outright.
    assert resolve_customer_name({"blackops_account_name": "Nokia", "other_blackops_account_name": "Ignored"}) == "Nokia"
    # hs_primary_company_name only used when both blackops fields are empty.
    assert resolve_customer_name({"hs_primary_company_name": "Acme"}) == "Acme"
    # HackerEarth's own CRM association never counts as a customer.
    assert resolve_customer_name({"hs_primary_company_name": "HackerEarth"}) is None
    assert resolve_customer_name({}) is None


def test_match_ticket():
    submitted_at = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
    ticket_info = {
        "t1": (submitted_at - timedelta(days=5), "owner1", "Alice"),
        "t2": (submitted_at - timedelta(hours=2), "owner2", "Bob"),  # closest
        "t3": (None, "owner3", "Carol"),  # no closed_at -- never picked
    }
    assert _match_ticket(submitted_at, ["t1", "t2", "t3"], ticket_info) == ("t2", "owner2", "Bob")
    # No candidates at all -- unmatched.
    assert _match_ticket(submitted_at, [], ticket_info) == (None, None, None)
    # Only a no-closed_at candidate -- still unmatched.
    assert _match_ticket(submitted_at, ["t3"], ticket_info) == (None, None, None)


def test_extract_channel():
    assert _extract_channel("Workflow: engg oncall\nChannel: #engg-assessment\nReported By: A") == "engg-assessment"
    assert _extract_channel("channel: Content-Programs ") == "content-programs"
    assert _extract_channel("Reported By: A") is None  # no Channel line
    assert _extract_channel("Channel:") is None  # empty value
    assert _extract_channel(None) is None


if __name__ == "__main__":
    test_split_categories()
    test_extract_channel()
    test_resolve_module()
    test_resolve_status()
    test_derive_priority()
    test_resolve_resolution_bucket()
    test_is_actionable()
    test_resolve_backline_path()
    test_ms_to_hours()
    test_to_bool()
    test_sla_met()
    test_resolve_customer_name()
    test_match_ticket()
    print("All transform checks passed.")
