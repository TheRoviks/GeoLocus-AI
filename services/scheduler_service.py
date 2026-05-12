from contextlib import suppress
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.keyboards.inline import reminder_done_kb
from core import strings
from core.logger import get_logger
from models.reminder import Reminder
from models.user import User
from services.quiet_hours import adjust_for_quiet_hours
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
            now = datetime.now(UTC)
            overdue_idx = 0
            for r in due:
                when = r.remind_at
                if when.tzinfo is None:
                    when = when.replace(tzinfo=UTC)
                if when < now:
                    when = now + timedelta(milliseconds=500 * overdue_idx)
                    overdue_idx += 1
                self._add_job(r.id, when)
            log.info("scheduler_started", restored=len(due), overdue=overdue_idx)

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
        now = datetime.now(UTC)
        if when < now:
            when = now
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
                log.warning(
                    "fire_user_inactive",
                    id=reminder_id,
                    user_id=rem.user_id,
                    user_missing=user is None,
                )
                next_rem_id: int | None = None
                next_rem_when: datetime | None = None
                if user is not None:
                    new_rem = await svc.create_next_recurrence(rem)
                    if new_rem is not None:
                        next_rem_id = new_rem.id
                        next_rem_when = new_rem.remind_at
                rem.is_done = True
                await session.commit()
                self.cancel(reminder_id)
                if next_rem_id is not None and next_rem_when is not None:
                    self._add_job(next_rem_id, next_rem_when)
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
                    reply_markup=reminder_done_kb(reminder_id),
                )
            except TelegramAPIError as exc:
                log.error("fire_send_failed", id=reminder_id, error=str(exc))
                return

            rem.notified_at = now_utc
            rem.is_done = True
            await session.commit()

            new_rem = await svc.create_next_recurrence(rem)
            if new_rem is not None:
                self._add_job(new_rem.id, new_rem.remind_at)
                log.info(
                    "recurring_next_scheduled",
                    id=new_rem.id,
                    at=new_rem.remind_at.isoformat(),
                )
