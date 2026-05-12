from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


def adjust_for_quiet_hours(
    when_utc: datetime,
    quiet_start: time,
    quiet_end: time,
    user_tz: str,
) -> datetime:
    tz = ZoneInfo(user_tz)
    local = when_utc.astimezone(tz)
    local_t = local.time()

    if quiet_start == quiet_end:
        return when_utc

    in_quiet = (
        (quiet_start < quiet_end and quiet_start <= local_t < quiet_end)
        or (quiet_start > quiet_end and (local_t >= quiet_start or local_t < quiet_end))
    )
    if not in_quiet:
        return when_utc

    target_date = local.date()
    if quiet_start > quiet_end and local_t >= quiet_start:
        target_date = (local + timedelta(days=1)).date()

    target_local = datetime.combine(target_date, quiet_end, tzinfo=tz)
    if target_local <= local:
        target_local += timedelta(days=1)
    return target_local.astimezone(when_utc.tzinfo or ZoneInfo("UTC"))
