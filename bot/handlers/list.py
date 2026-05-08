from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.formatting import fmt_when
from bot.handlers._callbacks import parse_callback_id
from core import strings
from models.user import User
from services.reminder_service import PER_PAGE, ReminderService
from services.scheduler_service import SchedulerService

router = Router(name="list")


def _build_list_kb(items, page: int, total_pages: int) -> InlineKeyboardMarkup:  # type: ignore[no-untyped-def]
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"🗑 {idx}",
                callback_data=f"list:del:{r.id}",
            )
        ]
        for idx, r in enumerate(items, start=1)
    ]
    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 1:
            nav.append(InlineKeyboardButton(text="←", callback_data=f"list:page:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(text="→", callback_data=f"list:page:{page + 1}"))
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _render_list(items, page: int, total: int, user_tz: str) -> tuple[str, InlineKeyboardMarkup]:  # type: ignore[no-untyped-def]
    total_pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    parts = [strings.LIST_HEADER.format(page=page, total_pages=total_pages)]
    for idx, r in enumerate(items, start=1):
        parts.append(
            strings.LIST_ITEM.format(
                idx=idx,
                recurring="🔁 " if r.is_recurring else "",
                text=r.parsed_text,
                when=fmt_when(r.remind_at, user_tz),
            )
        )
    return "".join(parts), _build_list_kb(items, page, total_pages)


@router.message(Command("list"))
@router.message(F.text == "📋 Список")
async def on_list(message: Message, user: User, session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        svc = ReminderService(session)
        items, total = await svc.get_active_for_user(user.id, page=1)

    if total == 0:
        await message.answer(strings.EMPTY_LIST)
        return

    text, kb = _render_list(items, 1, total, user.timezone)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("list:page:"))
async def on_page(
    cb: CallbackQuery, user: User, session_factory: async_sessionmaker
) -> None:
    page = parse_callback_id(cb.data, "list:page:")
    if page is None or page < 1:
        await cb.answer(strings.CALLBACK_INVALID, show_alert=True)
        return
    async with session_factory() as session:
        svc = ReminderService(session)
        items, total = await svc.get_active_for_user(user.id, page=page)
    if total == 0:
        await cb.message.edit_text(strings.EMPTY_LIST)  # type: ignore[union-attr]
        return
    text, kb = _render_list(items, page, total, user.timezone)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")  # type: ignore[union-attr]
    await cb.answer()


@router.callback_query(F.data.startswith("list:del:"))
async def on_delete(
    cb: CallbackQuery,
    user: User,
    session_factory: async_sessionmaker,
    scheduler: SchedulerService,
) -> None:
    rid = parse_callback_id(cb.data, "list:del:")
    if rid is None:
        await cb.answer(strings.CALLBACK_INVALID, show_alert=True)
        return
    async with session_factory() as session:
        svc = ReminderService(session)
        ok = await svc.soft_delete(rid, user.id)
    if ok:
        scheduler.cancel(rid)
        await cb.answer(strings.REMINDER_DELETED)
    else:
        await cb.answer(strings.REMINDER_NOT_FOUND, show_alert=True)
        return
    # refresh list
    async with session_factory() as session:
        svc = ReminderService(session)
        items, total = await svc.get_active_for_user(user.id, page=1)
    if total == 0:
        await cb.message.edit_text(strings.EMPTY_LIST)  # type: ignore[union-attr]
        return
    text, kb = _render_list(items, 1, total, user.timezone)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")  # type: ignore[union-attr]


@router.callback_query(F.data == "noop")
async def on_noop(cb: CallbackQuery) -> None:
    await cb.answer()


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def on_stats(message: Message, user: User, session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        svc = ReminderService(session)
        active, done = await svc.stats_for_user(user.id)
    await message.answer(
        strings.STATS.format(active=active, done=done),
        parse_mode="HTML",
    )


@router.message(Command("delete"))
async def on_delete_help(message: Message) -> None:
    await message.answer(
        "Используй /list — там у каждого напоминания есть кнопка 🗑 Удалить."
    )
