from calendar import monthrange
from datetime import UTC, datetime, timedelta

from core.exceptions import InvalidRecurrenceError


def _safe_replace(base: datetime, *, year: int, month: int, day: int) -> datetime:
    tz = base.tzinfo
    if tz is None or tz is UTC or type(tz).__name__ == "timezone":
        return base.replace(year=year, month=month, day=day)
    local = datetime(
        year, month, day,
        base.hour, base.minute, base.second, base.microsecond,
        tzinfo=tz, fold=0,
    )
    return local.astimezone(tz)


WEEKDAYS = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
}


def next_occurrence(rule: str, after: datetime) -> datetime:
    rule = rule.strip()

    if rule == "daily":
        return after + timedelta(days=1)

    if rule.startswith("weekly:"):
        day_code = rule.split(":", 1)[1].strip().upper()
        if day_code not in WEEKDAYS:
            raise InvalidRecurrenceError(f"Unknown weekday: {day_code}")
        target_dow = WEEKDAYS[day_code]
        days_ahead = (target_dow - after.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return after + timedelta(days=days_ahead)

    if rule.startswith("monthly:"):
        try:
            day = int(rule.split(":", 1)[1].strip())
        except ValueError as exc:
            raise InvalidRecurrenceError(f"Bad monthly rule: {rule}") from exc
        if not 1 <= day <= 31:
            raise InvalidRecurrenceError(f"Day must be 1..31: got {day}")

        year, month = after.year, after.month
        candidate = _safe_replace(
            after, year=year, month=month, day=min(day, monthrange(year, month)[1])
        )
        if candidate > after:
            return candidate
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        return _safe_replace(
            after, year=year, month=month, day=min(day, monthrange(year, month)[1])
        )

    raise InvalidRecurrenceError(f"Unknown rule: {rule}")
