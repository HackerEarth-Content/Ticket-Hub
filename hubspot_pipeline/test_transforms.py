"""Self-check for the transform logic: run `python hubspot_pipeline/test_transforms.py`."""

from hubspot_pipeline.category_map import resolve_module, split_categories
from hubspot_pipeline.priority import derive_priority
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


if __name__ == "__main__":
    test_split_categories()
    test_resolve_module()
    test_resolve_status()
    test_derive_priority()
    print("All transform checks passed.")
