from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_per_second: float = 1.0) -> None:
        self._cache: TTLCache[int, bool] = TTLCache(maxsize=10_000, ttl=rate_per_second)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)) and event.from_user is not None:
            uid = event.from_user.id
            if uid in self._cache:
                if isinstance(event, CallbackQuery):
                    await event.answer()
                return None
            self._cache[uid] = True
        return await handler(event, data)
