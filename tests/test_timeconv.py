import pytest
from docs_search_mcp.timeconv import TimeError, convert_time


def test_winter_and_summer_offsets_differ():
    w = convert_time("Europe/Warsaw", "10:00", "Asia/Dubai", "2026-01-15")
    s = convert_time("Europe/Warsaw", "10:00", "Asia/Dubai", "2026-07-15")
    assert w["target"]["datetime"].startswith("2026-01-15T13:00")   # CET UTC+1 -> UTC+4
    assert s["target"]["datetime"].startswith("2026-07-15T12:00")   # CEST UTC+2 -> UTC+4
    assert w["hours_ahead_of_source"] == 3 and s["hours_ahead_of_source"] == 2
    assert s["source"]["is_dst"] is True and w["source"]["is_dst"] is False


def test_date_rollover_and_weekday():
    r = convert_time("Europe/Warsaw", "23:30", "Asia/Tokyo", "2026-03-02")
    assert r["target"]["datetime"].startswith("2026-03-03T07:30")
    assert r["target"]["weekday"] == "Tuesday"


def test_fractional_offset():
    assert convert_time("UTC", "12:00", "Asia/Kathmandu", "2026-01-01")["hours_ahead_of_source"] == 5.75


def test_nonexistent_time_in_spring_forward():
    with pytest.raises(TimeError, match="does not exist"):
        convert_time("Europe/Warsaw", "02:30", "UTC", "2026-03-29")


def test_ambiguous_time_warns():
    r = convert_time("Europe/Warsaw", "02:30", "UTC", "2026-10-25")
    assert "twice" in r["warning"]


@pytest.mark.parametrize("args", [
    ("Mars/Base", "10:00", "UTC", None), ("UTC", "25:00", "UTC", None), ("UTC", "10am", "UTC", None),
    ("UTC", "10:00", "UTC", "2026-13-40"), ("UTC", "10:00", "Nope/Zone", None)])
def test_invalid_inputs(args):
    with pytest.raises(TimeError):
        convert_time(*args)
