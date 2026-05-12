from datetime import time

import pytest

from services.user_service import UserService


@pytest.mark.asyncio
async def test_get_or_create_creates_new(session):
    svc = UserService(session, default_tz="Europe/Moscow")
    user, created = await svc.get_or_create(99, "user99", "Ninety")
    assert created is True
    assert user.telegram_id == 99
    assert user.timezone == "Europe/Moscow"


@pytest.mark.asyncio
async def test_get_or_create_idempotent(session):
    svc = UserService(session)
    u1, c1 = await svc.get_or_create(99, "user99", "Ninety")
    u2, c2 = await svc.get_or_create(99, "user99", "Ninety")
    assert c1 is True
    assert c2 is False
    assert u1.id == u2.id


@pytest.mark.asyncio
async def test_get_or_create_updates_changed_fields(session):
    svc = UserService(session)
    _u1, _ = await svc.get_or_create(99, "old", "Old")
    u2, _ = await svc.get_or_create(99, "new", "New")
    assert u2.username == "new"
    assert u2.first_name == "New"


@pytest.mark.asyncio
async def test_update_timezone_and_quiet(session, user):
    svc = UserService(session)
    await svc.update_timezone(user.id, "UTC")
    await svc.update_quiet_hours(user.id, time(22, 0), time(7, 0))
    fetched = await svc.get_by_telegram_id(user.telegram_id)
    assert fetched is not None
    assert fetched.timezone == "UTC"
    assert fetched.quiet_hours_start == time(22, 0)


@pytest.mark.asyncio
async def test_update_missing_user_raises(session):
    import pytest as _pytest

    from core.exceptions import BotError
    svc = UserService(session)
    with _pytest.raises(BotError, match="User 99999 not found"):
        await svc.update_timezone(99999, "UTC")
