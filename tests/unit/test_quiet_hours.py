from datetime import UTC, datetime, time

from services.quiet_hours import adjust_for_quiet_hours

UTC = UTC


def test_outside_quiet_returns_as_is():
    when = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)  # 15:00 MSK
    out = adjust_for_quiet_hours(when, time(23, 0), time(8, 0), "Europe/Moscow")
    assert out == when


def test_inside_wrap_quiet_shifts_to_end():
    # 02:00 MSK is inside 23:00→08:00 window. Should shift to 08:00 MSK same day.
    when = datetime(2026, 5, 7, 23, 0, tzinfo=UTC)  # 02:00 MSK on 2026-05-08
    out = adjust_for_quiet_hours(when, time(23, 0), time(8, 0), "Europe/Moscow")
    # Expected: 08:00 MSK on 2026-05-08 = 05:00 UTC
    assert out == datetime(2026, 5, 8, 5, 0, tzinfo=UTC)


def test_inside_late_evening_wrap_shifts_to_next_morning():
    # 23:30 MSK 2026-05-08 → quiet → next morning 08:00 MSK 2026-05-09
    when = datetime(2026, 5, 8, 20, 30, tzinfo=UTC)  # 23:30 MSK
    out = adjust_for_quiet_hours(when, time(23, 0), time(8, 0), "Europe/Moscow")
    assert out == datetime(2026, 5, 9, 5, 0, tzinfo=UTC)


def test_disabled_when_start_equals_end():
    when = datetime(2026, 5, 8, 1, 0, tzinfo=UTC)
    out = adjust_for_quiet_hours(when, time(0, 0), time(0, 0), "Europe/Moscow")
    assert out == when


def test_non_wrap_window():
    # window 13:00-15:00 MSK. when 14:00 MSK → shift to 15:00 MSK
    when = datetime(2026, 5, 8, 11, 0, tzinfo=UTC)  # 14:00 MSK
    out = adjust_for_quiet_hours(when, time(13, 0), time(15, 0), "Europe/Moscow")
    assert out == datetime(2026, 5, 8, 12, 0, tzinfo=UTC)  # 15:00 MSK
