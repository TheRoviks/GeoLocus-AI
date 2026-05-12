from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BotError
from models.user import User


class UserService:
    def __init__(self, session: AsyncSession, default_tz: str = "Europe/Moscow") -> None:
        self._s = session
        self._default_tz = default_tz

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            changed = False
            if user.username != username:
                user.username = username
                changed = True
            if user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if changed:
                await self._s.commit()
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            timezone=self._default_tz,
        )
        self._s.add(user)
        await self._s.commit()
        await self._s.refresh(user)
        return user, True

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def update_timezone(self, user_id: int, tz: str) -> None:
        user = await self._s.get(User, user_id)
        if user is None:
            raise BotError(f"User {user_id} not found")
        user.timezone = tz
        await self._s.commit()

    async def update_quiet_hours(self, user_id: int, start: time, end: time) -> None:
        user = await self._s.get(User, user_id)
        if user is None:
            raise BotError(f"User {user_id} not found")
        user.quiet_hours_start = start
        user.quiet_hours_end = end
        await self._s.commit()
