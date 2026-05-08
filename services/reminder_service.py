from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ReminderNotFoundError
from models.reminder import Reminder

PER_PAGE = 5


class ReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self,
        user_id: int,
        text: str,
        parsed_text: str,
        remind_at: datetime,
        is_recurring: bool = False,
        recurrence_rule: str | None = None,
    ) -> Reminder:
        rem = Reminder(
            user_id=user_id,
            text=text,
            parsed_text=parsed_text,
            remind_at=remind_at,
            is_recurring=is_recurring,
            recurrence_rule=recurrence_rule,
        )
        self._s.add(rem)
        await self._s.commit()
        await self._s.refresh(rem)
        return rem

    async def get_by_id(self, reminder_id: int) -> Reminder | None:
        return await self._s.get(Reminder, reminder_id)

    async def get_active_for_user(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = PER_PAGE,
    ) -> tuple[list[Reminder], int]:
        page = max(page, 1)
        base = (
            select(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.is_deleted.is_(False),
                Reminder.is_done.is_(False),
            )
            .order_by(Reminder.remind_at.asc())
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._s.execute(count_stmt)).scalar_one()

        items_stmt = base.limit(per_page).offset((page - 1) * per_page)
        items = list((await self._s.execute(items_stmt)).scalars().all())
        return items, total

    async def soft_delete(self, reminder_id: int, user_id: int) -> bool:
        rem = await self.get_by_id(reminder_id)
        if rem is None or rem.user_id != user_id or rem.is_deleted:
            return False
        rem.is_deleted = True
        await self._s.commit()
        return True

    async def mark_done(self, reminder_id: int) -> Reminder:
        rem = await self.get_by_id(reminder_id)
        if rem is None:
            raise ReminderNotFoundError(str(reminder_id))
        rem.is_done = True
        rem.notified_at = datetime.now(UTC)
        await self._s.commit()
        return rem

    async def reschedule(self, reminder_id: int, new_time: datetime) -> Reminder:
        rem = await self.get_by_id(reminder_id)
        if rem is None:
            raise ReminderNotFoundError(str(reminder_id))
        rem.remind_at = new_time
        rem.is_done = False
        await self._s.commit()
        return rem

    async def get_due_for_restore(self) -> list[Reminder]:
        now = datetime.now(UTC)
        stmt = select(Reminder).where(
            Reminder.is_done.is_(False),
            Reminder.is_deleted.is_(False),
            Reminder.remind_at >= now,
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def stats_for_user(self, user_id: int) -> tuple[int, int]:
        active_stmt = select(func.count(Reminder.id)).where(
            Reminder.user_id == user_id,
            Reminder.is_deleted.is_(False),
            Reminder.is_done.is_(False),
        )
        done_stmt = select(func.count(Reminder.id)).where(
            Reminder.user_id == user_id,
            Reminder.is_deleted.is_(False),
            Reminder.is_done.is_(True),
        )
        active = (await self._s.execute(active_stmt)).scalar_one()
        done = (await self._s.execute(done_stmt)).scalar_one()
        return active, done
