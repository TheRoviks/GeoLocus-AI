from calendar import monthrange
from datetime import datetime, timedelta

from core.exceptions import InvalidRecurrenceError

WEEKDAYS: dict[str, int] = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
}


def next_occurrence(rule: str, after: datetime) -> datetime:
    """Compute the next datetime matching the recurrence rule, strictly after `after`.

    Supported formats:
    - "daily"
    - "weekly:MON" (or any 3-letter weekday code, uppercase)
    - "monthly:N" where N is 1..31; if month has fewer days, last day is used.
    """
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
        # try this month first
        last_day_this = monthrange(year, month)[1]
        candidate_day = min(day, last_day_this)
        candidate = after.replace(day=candidate_day)
        if candidate > after:
            return candidate
        # otherwise next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        last_day_next = monthrange(year, month)[1]
        return after.replace(year=year, month=month, day=min(day, last_day_next))

    raise InvalidRecurrenceError(f"Unknown rule: {rule}")
