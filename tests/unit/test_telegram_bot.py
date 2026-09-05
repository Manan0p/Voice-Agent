"""Unit and integration tests for Telegram Bot notification cards, callback handling, and webhooks."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from apps.agent.notifications.telegram.bot import TelegramCallbackHandler, TelegramCallNotifier
from apps.agent.telephony.handoff import HandoffManager
from apps.api.main import app
from packages.schemas.handoff import HandoffState
from packages.schemas.telegram import TelegramAlertPayload, TelegramCallbackAction


@pytest.mark.asyncio
async def test_telegram_alert_card_formatting():
    notifier = TelegramCallNotifier(bot_token="test_token", default_chat_id=123456)
    payload = TelegramAlertPayload(
        call_id="call-tg-1",
        caller_phone="+15551234567",
        caller_name="Alice Smith",
        intent="urgent_medical",
        urgency_score=5,
        risk_level="high",
        language="English",
        summary="Caller is requesting immediate doctor callback.",
    )

    text, reply_markup = notifier.format_alert_card(payload)

    assert "Alice Smith" in text
    assert "+15551234567" in text
    assert "CRITICAL (5/5)" in text
    assert "Urgent Medical" in text
    assert "call-tg-1" in text

    buttons = reply_markup["inline_keyboard"][0]
    assert len(buttons) == 3
    assert buttons[0]["text"] == "📞 Take Call"
    assert buttons[0]["callback_data"] == "handoff:take_call:call-tg-1"
    assert buttons[1]["text"] == "🤖 Keep AI"
    assert buttons[1]["callback_data"] == "handoff:keep_ai:call-tg-1"
    assert buttons[2]["text"] == "❌ End Call"
    assert buttons[2]["callback_data"] == "handoff:end_call:call-tg-1"


@pytest.mark.asyncio
async def test_send_call_alert_mock_and_summary():
    notifier = TelegramCallNotifier(bot_token="MOCK_TELEGRAM_TOKEN")
    payload = TelegramAlertPayload(

        call_id="call-tg-2",
        caller_phone="+919876543210",
        caller_name="Rajesh",
        intent="delivery",
        urgency_score=2,
    )

    result = await notifier.send_call_alert(payload, chat_id="998877")
    assert result.success is True
    assert result.chat_id == "998877"
    assert result.message_id is not None

    summary_res = await notifier.send_call_summary(
        call_id="call-tg-2",
        caller_name="Rajesh",
        summary_text="Package left with security.",
        duration_seconds=42,
        chat_id="998877",
    )
    assert summary_res.success is True
    assert summary_res.action == "summary"


@pytest.mark.asyncio
async def test_telegram_callback_handler_take_call():
    mock_ari = AsyncMock()
    mock_ari.create_bridge.return_value = AsyncMock(id="bridge-tg-1")
    mock_ari.add_channel_to_bridge.return_value = True

    handoff_mgr = HandoffManager(ari_client=mock_ari)
    handoff_mgr.register_call("call-tg-take", caller_phone="+1234567890")

    notifier = TelegramCallNotifier()
    notifier.update_call_card = AsyncMock(return_value=AsyncMock(success=True))

    handler = TelegramCallbackHandler(handoff_manager=handoff_mgr, notifier=notifier)

    res = await handler.handle_callback(
        callback_data="handoff:take_call:call-tg-take",
        chat_id=12345,
        message_id=55,
        target_endpoint="PJSIP/1002",
    )

    assert res["success"] is True
    assert res["call_id"] == "call-tg-take"
    assert res["action"] == TelegramCallbackAction.TAKE_CALL.value
    assert res["current_state"] == HandoffState.HUMAN_HANDLING.value

    status = handoff_mgr.get_status("call-tg-take")
    assert status.state == HandoffState.HUMAN_HANDLING
    assert notifier.update_call_card.called


@pytest.mark.asyncio
async def test_telegram_callback_handler_keep_ai_and_end():
    mock_ari = AsyncMock()
    handoff_mgr = HandoffManager(ari_client=mock_ari)
    handoff_mgr.register_call("call-tg-actions", caller_phone="+1234567890")

    notifier = TelegramCallNotifier()
    notifier.update_call_card = AsyncMock(return_value=AsyncMock(success=True))

    handler = TelegramCallbackHandler(handoff_manager=handoff_mgr, notifier=notifier)

    # Keep AI
    res_keep = await handler.handle_callback(
        callback_data="handoff:keep_ai:call-tg-actions",
        chat_id=12345,
        message_id=56,
    )
    assert res_keep["success"] is True
    assert res_keep["current_state"] == HandoffState.AI_HANDLING.value

    # End Call
    res_end = await handler.handle_callback(
        callback_data="handoff:end_call:call-tg-actions",
        chat_id=12345,
        message_id=56,
    )
    assert res_end["success"] is True
    assert res_end["current_state"] == HandoffState.COMPLETED.value


@pytest.mark.asyncio
async def test_telegram_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Alert endpoint
        alert_payload = {
            "call_id": "call-api-tg-1",
            "caller_phone": "+1999888777",
            "caller_name": "Test Contact",
            "intent": "general_inquiry",
            "urgency_score": 3,
            "risk_level": "low",
            "language": "English",
        }
        res = await client.post("/api/telegram/alert", json=alert_payload)
        assert res.status_code == 200
        assert res.json()["success"] is True

        # 2. Webhook callback query simulation
        webhook_body = {
            "update_id": 10001,
            "callback_query": {
                "id": "cb_1",
                "data": "handoff:keep_ai:call-api-tg-1",
                "message": {
                    "message_id": 991,
                    "chat": {"id": 12345},
                    "text": "Incoming Call Alert",
                },
            },
        }
        webhook_res = await client.post("/api/telegram/webhook", json=webhook_body)
        assert webhook_res.status_code == 200
        assert webhook_res.json()["ok"] is True
