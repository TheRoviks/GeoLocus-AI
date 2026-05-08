from datetime import datetime
from zoneinfo import ZoneInfo

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def fmt_when(when_utc: datetime, user_tz: str) -> str:
    local = when_utc.astimezone(ZoneInfo(user_tz))
    dow = WEEKDAYS_RU[local.weekday()]
    month = MONTHS_RU[local.month - 1]
    return f"{dow}, {local.day} {month} в {local.strftime('%H:%M')}"


def fmt_recurring(rule: str | None) -> str:
    if not rule:
        return ""
    if rule == "daily":
        return "  🔁 каждый день"
    if rule.startswith("weekly:"):
        code = rule.split(":", 1)[1]
        labels = {
            "MON": "по понедельникам", "TUE": "по вторникам", "WED": "по средам",
            "THU": "по четвергам", "FRI": "по пятницам", "SAT": "по субботам",
            "SUN": "по воскресеньям",
        }
        return f"  🔁 {labels.get(code, code)}"
    if rule.startswith("monthly:"):
        day = rule.split(":", 1)[1]
        return f"  🔁 {day} числа каждого месяца"
    return ""
