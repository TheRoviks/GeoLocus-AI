import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, Field, ValidationError

from core.config import Settings
from core.exceptions import AIParseError
from core.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """Ты парсер напоминаний. Получаешь текст на любом языке и возвращаешь ТОЛЬКО JSON.

Текущее время пользователя: {current_datetime}
Часовой пояс пользователя: {timezone}

Верни JSON со схемой:
{{
  "parsed_text": "что нужно сделать (кратко, в инфинитиве)",
  "remind_at": "ISO 8601 в TZ пользователя без смещения, напр. 2026-05-09T10:00:00",
  "is_recurring": true/false,
  "recurrence_rule": "daily | weekly:MON|TUE|WED|THU|FRI|SAT|SUN | monthly:1..31 | null",
  "confidence": 0.0-1.0
}}

Правила:
- "завтра" = следующий день в 10:00 если время не указано
- "утром" = 09:00, "днём" = 13:00, "вечером" = 19:00, "ночью" = 22:00
- "через X часов/минут" = текущее время + X
- "каждый день" → is_recurring=true, recurrence_rule="daily"
- "каждый понедельник" → recurrence_rule="weekly:MON"
- "каждое 5 число" → recurrence_rule="monthly:5"
- Если не можешь распарсить → confidence < 0.5

Только JSON, никакого текста вокруг.
"""


class ParsedReminder(BaseModel):
    parsed_text: str = Field(..., min_length=1, max_length=500)
    remind_at: datetime
    is_recurring: bool = False
    recurrence_rule: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class AIService:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.deepseek_api_key.get_secret_value()
        self._base_url = settings.deepseek_base_url.rstrip("/")
        self._model = settings.deepseek_model
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def parse(self, text: str, user_tz: str, now: datetime | None = None) -> ParsedReminder:
        if not text.strip():
            raise AIParseError("Empty text")

        tz = ZoneInfo(user_tz)
        local_now = (now or datetime.now(tz)).astimezone(tz)

        system = SYSTEM_PROMPT.format(
            current_datetime=local_now.strftime("%Y-%m-%d %H:%M (%A)"),
            timezone=user_tz,
        )
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text.strip()},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 300,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        for attempt in range(2):
            try:
                resp = await self._client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                log.error("deepseek_api_error", attempt=attempt, error=str(exc))
                if attempt == 1:
                    raise AIParseError(f"DeepSeek API error: {exc}") from exc
                continue

            try:
                body = resp.json()
                raw = body["choices"][0]["message"]["content"] or ""
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                log.warning("ai_bad_response_shape", attempt=attempt, error=str(exc))
                if attempt == 1:
                    raise AIParseError(f"Unexpected DeepSeek response: {exc}") from exc
                continue

            try:
                parsed = ParsedReminder.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                log.warning("ai_invalid_json", attempt=attempt, raw=raw[:200], error=str(exc))
                if attempt == 1:
                    raise AIParseError(f"AI returned invalid payload: {exc}") from exc
                continue

            if parsed.confidence < 0.5:
                log.info("ai_low_confidence", confidence=parsed.confidence, text=text)
                raise AIParseError(f"Low confidence: {parsed.confidence}")

            remind_at = parsed.remind_at
            if remind_at.tzinfo is None:
                remind_at = remind_at.replace(tzinfo=tz)
            parsed.remind_at = remind_at.astimezone(ZoneInfo("UTC"))
            return parsed

        raise AIParseError("Exhausted retries")
