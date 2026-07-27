"""Self-check for customer_matching.py and export.py's HMS formatter, using
values from the reference "Customer tickets raised.xlsx" workbook this
feature replicates. Run `python dashboard/test_customer_matching.py`."""

from dashboard.customer_matching import match_names
from dashboard.export import _format_hms


def test_match_names_collapses_aliases():
    ticket_names = ["Entri", "Datakrew Private Limited", "Modmed"]
    matched, unmatched = match_names(
        ["Entri India", "DataKrew", "Modmed (Non Tech)", "Modmed (Tech)", "Nonexistent Co"],
        ticket_names,
    )
    assert matched["Entri"] == ["Entri India"]
    assert matched["Datakrew Private Limited"] == ["DataKrew"]
    assert matched["Modmed"] == ["Modmed (Non Tech)", "Modmed (Tech)"]
    assert unmatched == ["Nonexistent Co"]


def test_format_hms_matches_reference_values():
    assert _format_hms(0.144722222222222) == "00:08:41"
    assert _format_hms(784.673888888889) == "784:40:26"


if __name__ == "__main__":
    test_match_names_collapses_aliases()
    test_format_hms_matches_reference_values()
    print("All customer_matching checks passed.")
