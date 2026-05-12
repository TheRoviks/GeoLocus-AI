from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from core.exceptions import InvalidRecurrenceError
from services.recurrence import next_occurrence


def test_daily_adds_one_day():
    after = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
    assert next_occurrence("daily", after) == datetime(2026, 5, 9, 10, 0, tzinfo=UTC)


def test_weekly_same_day_jumps_week():
    # 2026-05-08 is Friday
    after = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
    assert next_occurrence("weekly:FRI", after) == datetime(2026, 5, 15, 10, 0, tzinfo=UTC)


def test_weekly_mon_when_today_is_mon_gives_7_days():
    # 2026-05-11 is Monday
    after = datetime(2026, 5, 11, 9, 0, tzinfo=UTC)
    assert next_occurrence("weekly:MON", after) == datetime(2026, 5, 18, 9, 0, tzinfo=UTC)


def test_weekly_wed_when_today_is_mon_gives_2_days():
    after = datetime(2026, 5, 11, 9, 0, tzinfo=UTC)  # Monday
    assert next_occurrence("weekly:WED", after) == datetime(2026, 5, 13, 9, 0, tzinfo=UTC)


def test_weekly_other_weekday():
    after = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)  # Friday
    assert next_occurrence("weekly:MON", after) == datetime(2026, 5, 11, 10, 0, tzinfo=UTC)


def test_weekly_unknown_code_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("weekly:XXX", datetime.now(UTC))


def test_monthly_same_month_future():
    after = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    assert next_occurrence("monthly:15", after) == datetime(2026, 5, 15, 10, 0, tzinfo=UTC)


def test_monthly_rolls_over():
    after = datetime(2026, 5, 20, 10, 0, tzinfo=UTC)
    assert next_occurrence("monthly:15", after) == datetime(2026, 6, 15, 10, 0, tzinfo=UTC)


def test_monthly_year_boundary():
    after = datetime(2026, 12, 20, 10, 0, tzinfo=UTC)
    assert next_occurrence("monthly:5", after) == datetime(2027, 1, 5, 10, 0, tzinfo=UTC)


def test_monthly_short_month_clamps():
    # Feb 2027 has 28 days, asking for day=31 → clamped to 28
    after = datetime(2027, 1, 31, 10, 0, tzinfo=UTC)
    result = next_occurrence("monthly:31", after)
    assert result == datetime(2027, 2, 28, 10, 0, tzinfo=UTC)


def test_monthly_31_in_leap_february():
    # 2028 is a leap year → Feb 29
    after = datetime(2028, 1, 31, 10, 0, tzinfo=UTC)
    result = next_occurrence("monthly:31", after)
    assert result == datetime(2028, 2, 29, 10, 0, tzinfo=UTC)


def test_monthly_31_in_january_stays_31():
    after = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    result = next_occurrence("monthly:31", after)
    assert result == datetime(2026, 1, 31, 10, 0, tzinfo=UTC)


def test_monthly_day_already_passed_goes_next_month():
    # today is the 6th, want 5th → next month
    after = datetime(2026, 3, 6, 12, 0, tzinfo=UTC)
    result = next_occurrence("monthly:5", after)
    assert result.month == 4
    assert result.day == 5


def test_monthly_zero_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("monthly:0", datetime.now(UTC))


def test_monthly_32_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("monthly:32", datetime.now(UTC))


def test_invalid_rule_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("yearly", datetime.now(UTC))


def test_invalid_weekday_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("weekly:XYZ", datetime.now(UTC))


def test_invalid_monthly_day_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("monthly:99", datetime.now(UTC))


def test_dst_spring_forward_daily():
    # Europe/Berlin springs forward last Sunday of March.
    # Reminder on 2030-03-30 02:00 CET, next day crosses DST boundary.
    tz = ZoneInfo("Europe/Berlin")
    after = datetime(2030, 3, 30, 2, 0, tzinfo=tz)
    result = next_occurrence("daily", after)
    assert result.tzinfo is not None
    assert result.date().day == 31
