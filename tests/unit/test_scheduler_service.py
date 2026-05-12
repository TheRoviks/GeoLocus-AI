from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from services.reminder_service import ReminderService
from services.scheduler_service import SchedulerService


def _mock_bot() -> MagicMock:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest_asyncio.fixture()
async def user_no_quiet(session, user):
    """User with quiet hours disabled (start == end) so _fire always sends."""
    user.quiet_hours_start = time(0, 0)
    user.quiet_hours_end = time(0, 0)
    session.add(user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_fire_sends_and_marks_done(session_factory, user_no_quiet):
    user = user_no_quiet
    async with session_factory() as s:
        svc = ReminderService(s)
        rem = await svc.create(
            user_id=user.id, text="t", parsed_text="t",
            remind_at=datetime.now(UTC) + timedelta(minutes=1),
        )
    bot = _mock_bot()
    sched = SchedulerService(bot, session_factory)
    await sched.start()
    try:
        await sched._fire(rem.id)
        bot.send_message.assert_awaited_once()
        async with session_factory() as s:
            r = await ReminderService(s).get_by_id(rem.id)
            assert r.is_done is True
            assert r.notified_at is not None
    finally:
        await sched.shutdown()


@pytest.mark.asyncio
async def test_fire_skips_deleted(session_factory, user):
    async with session_factory() as s:
        svc = ReminderService(s)
        rem = await svc.create(
            user_id=user.id, text="t", parsed_text="t",
            remind_at=datetime.now(UTC) + timedelta(minutes=1),
        )
        await svc.soft_delete(rem.id, user.id)
    bot = _mock_bot()
    sched = SchedulerService(bot, session_factory)
    await sched.start()
    try:
        await sched._fire(rem.id)
        bot.send_message.assert_not_called()
    finally:
        await sched.shutdown()


@pytest.mark.asyncio
async def test_fire_recurring_creates_next(session_factory, user_no_quiet):
    user = user_no_quiet
    async with session_factory() as s:
        svc = ReminderService(s)
        rem = await svc.create(
            user_id=user.id, text="t", parsed_text="t",
            remind_at=datetime.now(UTC) + timedelta(minutes=1),
            is_recurring=True,
            recurrence_rule="daily",
        )
    bot = _mock_bot()
    sched = SchedulerService(bot, session_factory)
    await sched.start()
    try:
        await sched._fire(rem.id)
        async with session_factory() as s:
            svc = ReminderService(s)
            items, total = await svc.get_active_for_user(user.id)
            assert total == 1  # next recurrence
            assert items[0].is_recurring
            assert items[0].id != rem.id
    finally:
        await sched.shutdown()


@pytest.mark.asyncio
async def test_fire_quiet_hours_defers(session_factory, user, session):
    # set user quiet to wide window covering "now"
    from datetime import time
    from zoneinfo import ZoneInfo

    now_local = datetime.now(ZoneInfo(user.timezone))
    user.quiet_hours_start = time((now_local.hour - 1) % 24, 0)
    user.quiet_hours_end = time((now_local.hour + 1) % 24, 0)
    session.add(user)
    await session.commit()

    async with session_factory() as s:
        svc = ReminderService(s)
        rem = await svc.create(
            user_id=user.id, text="t", parsed_text="t",
            remind_at=datetime.now(UTC),
        )
    bot = _mock_bot()
    sched = SchedulerService(bot, session_factory)
    await sched.start()
    try:
        await sched._fire(rem.id)
        bot.send_message.assert_not_called()
        async with session_factory() as s:
            r = await ReminderService(s).get_by_id(rem.id)
            assert r.is_done is False
    finally:
        await sched.shutdown()


@pytest.mark.asyncio
async def test_fire_inactive_user_marks_done_no_send(session_factory, user, session):
    user.is_active = False
    session.add(user)
    await session.commit()

    async with session_factory() as s:
        rem = await ReminderService(s).create(
            user_id=user.id, text="x", parsed_text="x",
            remind_at=datetime(2030, 1, 1, tzinfo=UTC),
        )
    bot = _mock_bot()
    sched = SchedulerService(bot, session_factory)
    await sched.start()
    try:
        await sched._fire(rem.id)
        bot.send_message.assert_not_called()
        async with session_factory() as s:
            refreshed = await ReminderService(s).get_by_id(rem.id)
            assert refreshed.is_done is True
            assert refreshed.notified_at is None
    finally:
        await sched.shutdown()


@pytest.mark.asyncio
async def test_cancel_removes_job(session_factory):
    bot = _mock_bot()
    sched = SchedulerService(bot, session_factory)
    await sched.start()
    try:
        sched._add_job(42, datetime.now(UTC) + timedelta(hours=1))
        sched.cancel(42)
        assert sched._scheduler.get_job("rem-42") is None
        # idempotent
        sched.cancel(42)
    finally:
        await sched.shutdown()


@pytest.mark.asyncio
async def test_start_restores_jobs(session_factory, user):
    async with session_factory() as s:
        svc = ReminderService(s)
        await svc.create(
            user_id=user.id, text="t", parsed_text="t",
            remind_at=datetime.now(UTC) + timedelta(hours=2),
        )
        await svc.create(
            user_id=user.id, text="t2", parsed_text="t2",
            remind_at=datetime.now(UTC) + timedelta(hours=3),
        )
    bot = _mock_bot()
    sched = SchedulerService(bot, session_factory)
    await sched.start()
    try:
        jobs = sched._scheduler.get_jobs()
        assert len(jobs) == 2
    finally:
        await sched.shutdown()
