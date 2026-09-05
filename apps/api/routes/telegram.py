"""FastAPI router for Telegram Bot webhook updates and call notifications."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.agent.notifications.telegram.bot import TelegramCallbackHandler, TelegramCallNotifier
from apps.agent.telephony.handoff import HandoffManager
from apps.api.routes.handoff import get_handoff_manager
from packages.schemas.telegram import TelegramAlertPayload, TelegramNotificationResult

router = APIRouter(prefix="/api/telegram", tags=["Telegram Bot & Alerts"])


def get_telegram_notifier() -> TelegramCallNotifier:
    return TelegramCallNotifier()


def get_callback_handler(
    handoff_mgr: Annotated[HandoffManager, Depends(get_handoff_manager)],
    notifier: Annotated[TelegramCallNotifier, Depends(get_telegram_notifier)],
) -> TelegramCallbackHandler:
    return TelegramCallbackHandler(handoff_manager=handoff_mgr, notifier=notifier)


class TelegramWebhookUpdate(BaseModel):
    """Simplified Telegram webhook update schema."""

    update_id: int
    message: dict[str, Any] | None = None
    callback_query: dict[str, Any] | None = None


@router.post("/alert", response_model=TelegramNotificationResult)
async def send_triage_alert(
    payload: TelegramAlertPayload,
    notifier: Annotated[TelegramCallNotifier, Depends(get_telegram_notifier)],
) -> TelegramNotificationResult:
    """Dispatches a rich triage notification card to Telegram."""
    return await notifier.send_call_alert(payload)


@router.post("/webhook")
async def telegram_webhook(
    update: dict[str, Any],
    handler: Annotated[TelegramCallbackHandler, Depends(get_callback_handler)],
) -> dict[str, Any]:
    """Receives and processes incoming updates and inline button clicks from Telegram."""
    callback_query = update.get("callback_query")
    if callback_query:
        callback_data = callback_query.get("data", "")
        message = callback_query.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id", "0")
        message_id = message.get("message_id", 0)

        res = await handler.handle_callback(
            callback_data=callback_data,
            chat_id=chat_id,
            message_id=message_id,
        )
        return {"ok": True, "result": res}

    return {"ok": True, "ignored": True}
