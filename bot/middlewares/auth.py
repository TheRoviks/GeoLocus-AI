from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from services.user_service import UserService


class AuthMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker, default_tz: str) -> None:
        self._sf = session_factory
        self._default_tz = default_tz

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, Message | CallbackQuery):
            tg_user = event.from_user

        if tg_user is None:
            return await handler(event, data)

        async with self._sf() as session:
            svc = UserService(session, default_tz=self._default_tz)
            user, _created = await svc.get_or_create(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name or "",
            )
            data["user"] = user
            data["session_factory"] = self._sf

        return await handler(event, data)
