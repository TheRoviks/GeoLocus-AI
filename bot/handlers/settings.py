from datetime import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.keyboards.inline import quiet_kb, settings_menu, tz_kb
from core import strings
from models.user import User
from services.user_service import UserService

router = Router(name="settings")


def _menu_text(user: User) -> str:
    return strings.SETTINGS_MENU.format(
        tz=user.timezone,
        quiet_start=user.quiet_hours_start.strftime("%H:%M"),
        quiet_end=user.quiet_hours_end.strftime("%H:%M"),
    )


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def on_settings(message: Message, user: User) -> None:
    await message.answer(_menu_text(user), reply_markup=settings_menu(), parse_mode="HTML")


@router.callback_query(F.data == "settings:tz")
async def on_pick_tz(cb: CallbackQuery) -> None:
    await cb.message.edit_text(strings.SETTINGS_TZ_PROMPT, reply_markup=tz_kb())  # type: ignore[union-attr]
    await cb.answer()


@router.callback_query(F.data == "settings:quiet")
async def on_pick_quiet(cb: CallbackQuery) -> None:
    await cb.message.edit_text(strings.SETTINGS_QUIET_PROMPT, reply_markup=quiet_kb())  # type: ignore[union-attr]
    await cb.answer()


@router.callback_query(F.data == "settings:back")
async def on_back(cb: CallbackQuery, user: User) -> None:
    await cb.message.edit_text(_menu_text(user), reply_markup=settings_menu(), parse_mode="HTML")  # type: ignore[union-attr]
    await cb.answer()


@router.callback_query(F.data.startswith("settings:tz:"))
async def on_set_tz(
    cb: CallbackQuery, user: User, session_factory: async_sessionmaker
) -> None:
    tz = cb.data.split(":", 2)[2]  # type: ignore[union-attr]
    async with session_factory() as session:
        svc = UserService(session)
        await svc.update_timezone(user.id, tz)
    user.timezone = tz
    await cb.answer(strings.SETTINGS_UPDATED)
    await cb.message.edit_text(_menu_text(user), reply_markup=settings_menu(), parse_mode="HTML")  # type: ignore[union-attr]


@router.callback_query(F.data.startswith("settings:quiet:"))
async def on_set_quiet(
    cb: CallbackQuery, user: User, session_factory: async_sessionmaker
) -> None:
    val = cb.data.split(":", 2)[2]  # type: ignore[union-attr]
    if val == "off":
        start, end = time(0, 0), time(0, 0)
    else:
        s, e = val.split("-")
        sh, sm = map(int, s.split(":"))
        eh, em = map(int, e.split(":"))
        start, end = time(sh, sm), time(eh, em)

    async with session_factory() as session:
        svc = UserService(session)
        await svc.update_quiet_hours(user.id, start, end)
    user.quiet_hours_start = start
    user.quiet_hours_end = end
    await cb.answer(strings.SETTINGS_UPDATED)
    await cb.message.edit_text(_menu_text(user), reply_markup=settings_menu(), parse_mode="HTML")  # type: ignore[union-attr]
