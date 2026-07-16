"""Self-check for utils.py's pure helpers: run `python dashboard/test_utils.py`."""

from dashboard.utils import _NPS_DETRACTOR_MAX, _NPS_PROMOTER_MIN, _nps_bucket


def test_nps_bucket():
    assert _nps_bucket(_NPS_PROMOTER_MIN) == "promoter"
    assert _nps_bucket(10) == "promoter"
    assert _nps_bucket(_NPS_DETRACTOR_MAX) == "detractor"
    assert _nps_bucket(0) == "detractor"
    assert _nps_bucket(7) == "passive"
    assert _nps_bucket(8) == "passive"


if __name__ == "__main__":
    test_nps_bucket()
    print("All utils checks passed.")
