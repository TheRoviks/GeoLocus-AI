from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.formatting import fmt_recurring, fmt_when
from bot.handlers._callbacks import parse_callback_id
from bot.keyboards.inline import reminder_actions
from core import strings
from core.exceptions import AIParseError
from core.logger import get_logger
from models.user import User
from services.ai_service import AIService
from services.quiet_hours import adjust_for_quiet_hours
from services.reminder_service import ReminderService
from services.scheduler_service import SchedulerService

router = Router(name="reminders")
log = get_logger(__name__)

MENU_TEXTS = {"📋 Список", "📊 Статистика", "⚙️ Настройки", "❓ Помощь"}


@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(MENU_TEXTS))
async def on_text(
    message: Message,
    user: User,
    session_factory: async_sessionmaker,
    ai: AIService,
    scheduler: SchedulerService,
) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    try:
        parsed = await ai.parse(text, user_tz=user.timezone)
    except AIParseError as exc:
        log.info("ai_parse_failed", error=str(exc))
        await message.answer(strings.AI_ERROR)
        return

    async with session_factory() as session:
        svc = ReminderService(session)
        rem = await svc.create(
            user_id=user.id,
            text=text,
            parsed_text=parsed.parsed_text,
            remind_at=parsed.remind_at,
            is_recurring=parsed.is_recurring,
            recurrence_rule=parsed.recurrence_rule,
        )

    scheduler.schedule(rem)

    when = fmt_when(parsed.remind_at, user.timezone)
    recurring = fmt_recurring(parsed.recurrence_rule) if parsed.is_recurring else ""
    await message.answer(
        strings.REMINDER_CREATED.format(
            parsed_text=parsed.parsed_text,
            when=when,
            recurring=("\n" + recurring) if recurring else "",
        ),
        reply_markup=reminder_actions(rem.id),
    )


@router.callback_query(F.data.startswith("rem:cancel:"))
async def on_cancel(
    cb: CallbackQuery,
    user: User,
    session_factory: async_sessionmaker,
    scheduler: SchedulerService,
) -> None:
    rid = parse_callback_id(cb.data, "rem:cancel:")
    if rid is None:
        await cb.answer(strings.CALLBACK_INVALID, show_alert=True)
        return
    async with session_factory() as session:
        svc = ReminderService(session)
        ok = await svc.soft_delete(rid, user.id)
    if ok:
        scheduler.cancel(rid)
        await cb.answer(strings.REMINDER_DELETED)
        if isinstance(cb.message, Message):
            await cb.message.edit_reply_markup(reply_markup=None)
    else:
        await cb.answer(strings.REMINDER_NOT_FOUND, show_alert=True)


@router.callback_query(F.data.startswith("rem:done:"))
async def on_done(
    cb: CallbackQuery,
    user: User,
    session_factory: async_sessionmaker,
    scheduler: SchedulerService,
) -> None:
    rid = parse_callback_id(cb.data, "rem:done:")
    if rid is None:
        await cb.answer(strings.CALLBACK_INVALID, show_alert=True)
        return

    next_rem_id: int | None = None
    next_rem_when: datetime | None = None

    async with session_factory() as session:
        svc = ReminderService(session)
        rem = await svc.get_by_id(rid)
        if rem is None or rem.is_deleted or rem.is_done or rem.user_id != user.id:
            await cb.answer(strings.REMINDER_NOT_FOUND, show_alert=True)
            return
        rem.is_done = True
        rem.notified_at = datetime.now(UTC)
        await session.commit()

        new_rem = await svc.create_next_recurrence(rem)
        if new_rem is not None:
            next_rem_id = new_rem.id
            next_rem_when = new_rem.remind_at

    if next_rem_id is not None and next_rem_when is not None:
        scheduler.reschedule(next_rem_id, next_rem_when)

    await cb.answer(strings.REMINDER_DONE)
    if isinstance(cb.message, Message):
        await cb.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("rem:snooze:"))
async def on_snooze(
    cb: CallbackQuery,
    user: User,
    session_factory: async_sessionmaker,
    scheduler: SchedulerService,
) -> None:
    rid = parse_callback_id(cb.data, "rem:snooze:")
    if rid is None:
        await cb.answer(strings.CALLBACK_INVALID, show_alert=True)
        return

    new_time = datetime.now(UTC) + timedelta(minutes=10)
    new_time = adjust_for_quiet_hours(
        new_time,
        user.quiet_hours_start,
        user.quiet_hours_end,
        user.timezone,
    )
    async with session_factory() as session:
        svc = ReminderService(session)
        rem = await svc.get_by_id(rid)
        if rem is None or rem.is_deleted or rem.user_id != user.id:
            await cb.answer(strings.REMINDER_NOT_FOUND, show_alert=True)
            return
        rem = await svc.reschedule(rid, new_time)

    scheduler.reschedule(rid, rem.remind_at)
    await cb.answer(strings.REMINDER_SNOOZED)
    if isinstance(cb.message, Message):
        await cb.message.edit_reply_markup(reply_markup=None)
