import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import httpx
import pytest

from core.config import get_settings
from core.exceptions import AIParseError
from services.ai_service import AIService


def _mock_response(payload: dict | str) -> MagicMock:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    resp = MagicMock(spec=httpx.Response)
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"choices": [{"message": {"content": raw}}]})
    return resp


@pytest.fixture()
def ai_service(monkeypatch):
    svc = AIService(get_settings())
    return svc


@pytest.mark.asyncio
async def test_parse_simple_tomorrow(ai_service, monkeypatch):
    payload = {
        "parsed_text": "купить молоко",
        "remind_at": "2026-05-09T10:00:00",
        "is_recurring": False,
        "recurrence_rule": None,
        "confidence": 0.9,
    }
    post = AsyncMock(return_value=_mock_response(payload))
    monkeypatch.setattr(ai_service._client, "post", post)

    now = datetime(2026, 5, 8, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    result = await ai_service.parse("купить молоко завтра в 10", "Europe/Moscow", now=now)
    assert result.parsed_text == "купить молоко"
    assert result.remind_at.hour == 7
    assert result.remind_at.tzinfo is not None


@pytest.mark.asyncio
async def test_parse_recurring(ai_service, monkeypatch):
    payload = {
        "parsed_text": "зарядка",
        "remind_at": "2026-05-11T09:00:00",
        "is_recurring": True,
        "recurrence_rule": "weekly:MON",
        "confidence": 0.95,
    }
    post = AsyncMock(return_value=_mock_response(payload))
    monkeypatch.setattr(ai_service._client, "post", post)
    result = await ai_service.parse(
        "каждый понедельник делать зарядку в 9",
        "Europe/Moscow",
        now=datetime(2026, 5, 8, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    assert result.is_recurring
    assert result.recurrence_rule == "weekly:MON"


@pytest.mark.asyncio
async def test_parse_low_confidence_raises(ai_service, monkeypatch):
    payload = {
        "parsed_text": "?",
        "remind_at": "2026-05-09T10:00:00",
        "is_recurring": False,
        "recurrence_rule": None,
        "confidence": 0.1,
    }
    post = AsyncMock(return_value=_mock_response(payload))
    monkeypatch.setattr(ai_service._client, "post", post)
    with pytest.raises(AIParseError):
        await ai_service.parse("???", "Europe/Moscow")


@pytest.mark.asyncio
async def test_parse_empty_text_raises(ai_service):
    with pytest.raises(AIParseError):
        await ai_service.parse("   ", "Europe/Moscow")


@pytest.mark.asyncio
async def test_parse_invalid_json_retries_then_fails(ai_service, monkeypatch):
    post = AsyncMock(return_value=_mock_response("not a json {"))
    monkeypatch.setattr(ai_service._client, "post", post)
    with pytest.raises(AIParseError):
        await ai_service.parse("текст", "Europe/Moscow")
    assert post.await_count == 2


@pytest.mark.asyncio
async def test_parse_invalid_then_valid(ai_service, monkeypatch):
    good = {
        "parsed_text": "ok",
        "remind_at": "2026-05-09T10:00:00",
        "is_recurring": False,
        "recurrence_rule": None,
        "confidence": 0.9,
    }
    post = AsyncMock(side_effect=[_mock_response("oops"), _mock_response(good)])
    monkeypatch.setattr(ai_service._client, "post", post)
    result = await ai_service.parse(
        "ok", "Europe/Moscow",
        now=datetime(2026, 5, 8, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    assert result.parsed_text == "ok"


@pytest.mark.asyncio
async def test_parse_api_error_propagates(ai_service, monkeypatch):
    request = httpx.Request("POST", "https://example.com")
    post = AsyncMock(side_effect=httpx.ConnectError("boom", request=request))
    monkeypatch.setattr(ai_service._client, "post", post)
    with pytest.raises(AIParseError):
        await ai_service.parse("текст", "Europe/Moscow")
