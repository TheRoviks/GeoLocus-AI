from datetime import UTC, datetime, timedelta

import pytest

from core.exceptions import ReminderNotFoundError
from services.reminder_service import ReminderService

UTC = UTC


@pytest.mark.asyncio
async def test_create_and_get(session, user):
    svc = ReminderService(session)
    rem = await svc.create(
        user_id=user.id,
        text="купить молоко",
        parsed_text="купить молоко",
        remind_at=datetime(2030, 1, 1, 12, 0, tzinfo=UTC),
    )
    fetched = await svc.get_by_id(rem.id)
    assert fetched is not None
    assert fetched.parsed_text == "купить молоко"


@pytest.mark.asyncio
async def test_get_active_pagination(session, user):
    svc = ReminderService(session)
    base = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
    for i in range(7):
        await svc.create(
            user_id=user.id,
            text=f"t{i}",
            parsed_text=f"t{i}",
            remind_at=base + timedelta(days=i),
        )
    page1, total = await svc.get_active_for_user(user.id, page=1)
    assert total == 7
    assert len(page1) == 5

    page2, _ = await svc.get_active_for_user(user.id, page=2)
    assert len(page2) == 2


@pytest.mark.asyncio
async def test_soft_delete(session, user):
    svc = ReminderService(session)
    rem = await svc.create(
        user_id=user.id,
        text="x",
        parsed_text="x",
        remind_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    assert await svc.soft_delete(rem.id, user.id) is True
    _items, total = await svc.get_active_for_user(user.id)
    assert total == 0
    # double delete returns False
    assert await svc.soft_delete(rem.id, user.id) is False


@pytest.mark.asyncio
async def test_delete_other_users_reminder_blocked(session, user):
    svc = ReminderService(session)
    rem = await svc.create(
        user_id=user.id,
        text="x",
        parsed_text="x",
        remind_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    assert await svc.soft_delete(rem.id, user_id=99999) is False


@pytest.mark.asyncio
async def test_mark_done(session, user):
    svc = ReminderService(session)
    rem = await svc.create(
        user_id=user.id, text="x", parsed_text="x",
        remind_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    done = await svc.mark_done(rem.id)
    assert done.is_done is True
    assert done.notified_at is not None


@pytest.mark.asyncio
async def test_mark_done_missing(session):
    svc = ReminderService(session)
    with pytest.raises(ReminderNotFoundError):
        await svc.mark_done(99999)


@pytest.mark.asyncio
async def test_stats(session, user):
    svc = ReminderService(session)
    a = await svc.create(user_id=user.id, text="a", parsed_text="a",
                         remind_at=datetime(2030, 1, 1, tzinfo=UTC))
    await svc.create(user_id=user.id, text="b", parsed_text="b",
                     remind_at=datetime(2030, 1, 2, tzinfo=UTC))
    await svc.mark_done(a.id)
    active, done = await svc.stats_for_user(user.id)
    assert active == 1
    assert done == 1


@pytest.mark.asyncio
async def test_get_due_for_restore_filters(session, user):
    svc = ReminderService(session)
    past = datetime.now(UTC) - timedelta(days=1)
    future = datetime.now(UTC) + timedelta(days=1)
    p = await svc.create(user_id=user.id, text="p", parsed_text="p", remind_at=past)
    f = await svc.create(user_id=user.id, text="f", parsed_text="f", remind_at=future)
    d = await svc.create(user_id=user.id, text="d", parsed_text="d", remind_at=future)
    await svc.soft_delete(d.id, user.id)

    due = await svc.get_due_for_restore()
    ids = {r.id for r in due}
    assert f.id in ids
    assert p.id not in ids
    assert d.id not in ids
