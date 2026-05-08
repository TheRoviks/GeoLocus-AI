from contextlib import suppress
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import async_sessionmaker

from core import strings
from core.exceptions import InvalidRecurrenceError
from core.logger import get_logger
from models.reminder import Reminder
from models.user import User
from services.quiet_hours import adjust_for_quiet_hours
from services.recurrence import next_occurrence
from services.reminder_service import ReminderService

log = get_logger(__name__)


def _job_id(reminder_id: int) -> str:
    return f"rem-{reminder_id}"


class SchedulerService:
    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker,
    ) -> None:
        self._bot = bot
        self._sf = session_factory
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    async def start(self) -> None:
        self._scheduler.start()
        async with self._sf() as session:
            svc = ReminderService(session)
            due = await svc.get_due_for_restore()
            for r in due:
                self._add_job(r.id, r.remind_at)
            log.info("scheduler_started", restored=len(due))

    async def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    def schedule(self, reminder: Reminder) -> None:
        self._add_job(reminder.id, reminder.remind_at)

    def cancel(self, reminder_id: int) -> None:
        with suppress(JobLookupError):
            self._scheduler.remove_job(_job_id(reminder_id))

    def reschedule(self, reminder_id: int, when: datetime) -> None:
        self.cancel(reminder_id)
        self._add_job(reminder_id, when)

    def _add_job(self, reminder_id: int, when: datetime) -> None:
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        self._scheduler.add_job(
            self._fire,
            trigger=DateTrigger(run_date=when),
            args=[reminder_id],
            id=_job_id(reminder_id),
            replace_existing=True,
            misfire_grace_time=300,
        )

    async def _fire(self, reminder_id: int) -> None:
        async with self._sf() as session:
            svc = ReminderService(session)
            rem = await svc.get_by_id(reminder_id)
            if rem is None or rem.is_deleted or rem.is_done:
                log.info("fire_skipped", id=reminder_id)
                return

            user = await session.get(User, rem.user_id)
            if user is None or not user.is_active:
                return

            now_utc = datetime.now(UTC)
            adjusted = adjust_for_quiet_hours(
                now_utc,
                user.quiet_hours_start,
                user.quiet_hours_end,
                user.timezone,
            )
            if adjusted > now_utc:
                log.info("fire_deferred_quiet", id=reminder_id, until=adjusted.isoformat())
                self.reschedule(reminder_id, adjusted)
                return

            try:
                await self._bot.send_message(
                    chat_id=user.telegram_id,
                    text=strings.REMINDER_FIRED.format(parsed_text=rem.parsed_text),
                    reply_markup=_done_kb(reminder_id),
                )
            except TelegramAPIError as exc:
                log.error("fire_send_failed", id=reminder_id, error=str(exc))
                return

            rem.notified_at = now_utc
            rem.is_done = True
            await session.commit()

            if rem.is_recurring and rem.recurrence_rule:
                try:
                    next_at = next_occurrence(rem.recurrence_rule, rem.remind_at)
                except InvalidRecurrenceError as exc:
                    log.error("bad_recurrence", id=reminder_id, error=str(exc))
                    return
                new_rem = await svc.create(
                    user_id=rem.user_id,
                    text=rem.text,
                    parsed_text=rem.parsed_text,
                    remind_at=next_at,
                    is_recurring=True,
                    recurrence_rule=rem.recurrence_rule,
                )
                self._add_job(new_rem.id, new_rem.remind_at)
                log.info("recurring_next_scheduled", id=new_rem.id, at=next_at.isoformat())


def _done_kb(reminder_id: int):  # type: ignore[no-untyped-def]
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Готово", callback_data=f"rem:done:{reminder_id}"),
                InlineKeyboardButton(text="⏰ +10 мин", callback_data=f"rem:snooze:{reminder_id}"),
            ]
        ]
    )
