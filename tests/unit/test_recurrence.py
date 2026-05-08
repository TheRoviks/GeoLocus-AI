from datetime import UTC, datetime

import pytest

from core.exceptions import InvalidRecurrenceError
from services.recurrence import next_occurrence

UTC = UTC


def test_daily_adds_one_day():
    after = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
    assert next_occurrence("daily", after) == datetime(2026, 5, 9, 10, 0, tzinfo=UTC)


def test_weekly_same_day_jumps_week():
    # 2026-05-08 is Friday
    after = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)
    assert next_occurrence("weekly:FRI", after) == datetime(2026, 5, 15, 10, 0, tzinfo=UTC)


def test_weekly_other_weekday():
    after = datetime(2026, 5, 8, 10, 0, tzinfo=UTC)  # Friday
    assert next_occurrence("weekly:MON", after) == datetime(2026, 5, 11, 10, 0, tzinfo=UTC)


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


def test_invalid_rule_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("yearly", datetime.now(UTC))


def test_invalid_weekday_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("weekly:XYZ", datetime.now(UTC))


def test_invalid_monthly_day_raises():
    with pytest.raises(InvalidRecurrenceError):
        next_occurrence("monthly:99", datetime.now(UTC))
