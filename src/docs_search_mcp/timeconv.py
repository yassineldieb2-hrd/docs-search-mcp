"""Timezone conversion.

Idea adapted from the `time` server in modelcontextprotocol/servers (MIT). Differences: an
optional date (so DST is right for a *given day*, not just today), explicit handling of times
that do not exist / are ambiguous around DST changes, and ISO 'YYYY-MM-DD' validation.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TimeError(ValueError):
    pass


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        raise TimeError(f"unknown timezone '{name}'. Use an IANA name such as 'Europe/Warsaw'") from None


def _describe(dt: datetime, zone_name: str) -> dict:
    return {"timezone": zone_name, "datetime": dt.isoformat(timespec="minutes"),
            "weekday": dt.strftime("%A"), "utc_offset": dt.strftime("%z"), "is_dst": bool(dt.dst())}


def convert_time(source_timezone: str, time: str, target_timezone: str,
                 on_date: str | None = None) -> dict:
    src, dst = _zone(source_timezone), _zone(target_timezone)
    try:
        hh, mm = datetime.strptime(time, "%H:%M").hour, datetime.strptime(time, "%H:%M").minute
    except ValueError:
        raise TimeError("time must be 24-hour 'HH:MM'") from None
    if on_date:
        try:
            day = date.fromisoformat(on_date)
        except ValueError:
            raise TimeError("date must be 'YYYY-MM-DD'") from None
    else:
        day = datetime.now(src).date()
    local = datetime(day.year, day.month, day.day, hh, mm, tzinfo=src)
    # A wall-clock time that does not exist (spring forward) does not survive a UTC round trip.
    roundtrip = local.astimezone(timezone.utc).astimezone(src).replace(tzinfo=None)
    if roundtrip != local.replace(tzinfo=None):
        raise TimeError(f"{time} on {day} does not exist in {source_timezone} (clocks move forward)") from None
    target = local.astimezone(dst)
    diff = (target.utcoffset() - local.utcoffset()).total_seconds() / 3600
    result = {"source": _describe(local, source_timezone), "target": _describe(target, target_timezone),
              "hours_ahead_of_source": diff}
    # fold=0 and fold=1 differ when the hour repeats (fall back)
    if local.replace(fold=1).utcoffset() != local.utcoffset():
        result["warning"] = "this wall-clock time occurs twice on that day (clocks move back); first occurrence used"
    return result
