import os
from collections.abc import AsyncIterator
from datetime import UTC, time

# Set test env BEFORE any project imports load Settings.
os.environ.setdefault("BOT_TOKEN", "test:token")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DEFAULT_TIMEZONE", "Europe/Moscow")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import Base, Reminder, User


@pytest_asyncio.fixture()
async def engine() -> AsyncIterator:
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture()
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture()
async def session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture()
async def user(session) -> User:
    u = User(
        telegram_id=12345,
        username="tester",
        first_name="Tester",
        timezone="Europe/Moscow",
        quiet_hours_start=time(23, 0),
        quiet_hours_end=time(8, 0),
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest.fixture()
def make_reminder(user):
    def _make(**kw):
        from datetime import datetime
        defaults = dict(
            user_id=user.id,
            text="t",
            parsed_text="pt",
            remind_at=datetime(2030, 1, 1, 12, 0, tzinfo=UTC),
        )
        defaults.update(kw)
        return Reminder(**defaults)
    return _make
