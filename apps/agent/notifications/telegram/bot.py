"""Telegram Bot notification engine and realtime human intervention callback handler.

Supports rich HTML/Markdown call alert cards with inline interactive buttons:
[📞 Take Call] [🤖 Keep AI] [❌ End Call]
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from apps.agent.telephony.handoff import HandoffManager
from packages.schemas.telegram import (
    TelegramAlertPayload,
    TelegramCallbackAction,
    TelegramNotificationResult,
)
from packages.shared.config import get_settings

logger = logging.getLogger(__name__)


class TelegramCallNotifier:
    """Sends async call triage alerts, transcript updates, and post-call debriefs to Telegram."""

    def __init__(
        self,
        bot_token: str | None = None,
        default_chat_id: str | int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.bot_token = bot_token if bot_token is not None else settings.telegram_bot_token
        self.default_chat_id = (
            default_chat_id if default_chat_id is not None else settings.telegram_chat_id
        )
        self._client = http_client
        self._api_base = f"https://api.telegram.org/bot{self.bot_token}"

    def format_alert_card(self, payload: TelegramAlertPayload) -> tuple[str, dict[str, Any]]:
        """Formats rich HTML message text and inline keyboard buttons."""
        urgency_icons = {
            1: "🟢 Low (1/5)",
            2: "🔵 Low-Med (2/5)",
            3: "🟡 Medium (3/5)",
            4: "🟠 High (4/5)",
            5: "🔴 CRITICAL (5/5)",
        }
        urgency_str = urgency_icons.get(
            payload.urgency_score, f"Urgency: {payload.urgency_score}/5"
        )

        intent_icon = "📞"
        if "delivery" in payload.intent.lower():
            intent_icon = "📦"
        elif "emergency" in payload.intent.lower():
            intent_icon = "🚨"
        elif "spam" in payload.intent.lower():
            intent_icon = "🛑"
        elif "recruiter" in payload.intent.lower() or "job" in payload.intent.lower():
            intent_icon = "💼"

        text = (
            f"<b>{intent_icon} Incoming Call Alert</b>\n\n"
            f"👤 <b>Caller:</b> {payload.caller_name} (<code>{payload.caller_phone}</code>)\n"
            f"🎯 <b>Intent:</b> {payload.intent.replace('_', ' ').title()}\n"
            f"📊 <b>Urgency:</b> {urgency_str}\n"
            f"🛡️ <b>Risk:</b> {payload.risk_level.upper()}\n"
            f"🗣️ <b>Language:</b> {payload.language}\n"
        )

        if payload.summary:
            text += f"\n📝 <b>Live Summary:</b>\n<i>{payload.summary}</i>\n"

        text += f"\n🆔 <code>{payload.call_id}</code>"

        # Inline Action Keyboard
        inline_keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📞 Take Call",
                        "callback_data": f"handoff:{TelegramCallbackAction.TAKE_CALL.value}:{payload.call_id}",
                    },
                    {
                        "text": "🤖 Keep AI",
                        "callback_data": f"handoff:{TelegramCallbackAction.KEEP_AI.value}:{payload.call_id}",
                    },
                    {
                        "text": "❌ End Call",
                        "callback_data": f"handoff:{TelegramCallbackAction.END_CALL.value}:{payload.call_id}",
                    },
                ]
            ]
        }

        return text, inline_keyboard

    async def send_call_alert(
        self,
        payload: TelegramAlertPayload,
        chat_id: str | int | None = None,
    ) -> TelegramNotificationResult:
        """Sends a rich triage alert card with interactive inline buttons."""
        target_chat = chat_id or self.default_chat_id
        text, reply_markup = self.format_alert_card(payload)

        # If running in mock / test environment without real token
        if self.bot_token == "MOCK_TELEGRAM_TOKEN" or not self.bot_token:
            logger.info("Mock Telegram alert sent to %s for call %s", target_chat, payload.call_id)
            return TelegramNotificationResult(
                success=True,
                chat_id=target_chat,
                message_id=999001,
                action="send",
            )

        client = self._client or httpx.AsyncClient()
        try:
            url = f"{self._api_base}/sendMessage"
            body = {
                "chat_id": target_chat,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": reply_markup,
            }
            res = await client.post(url, json=body, timeout=5.0)
            data = res.json()
            if res.is_success and data.get("ok"):
                msg_id = data.get("result", {}).get("message_id")
                return TelegramNotificationResult(
                    success=True,
                    chat_id=target_chat,
                    message_id=msg_id,
                    action="send",
                )
            return TelegramNotificationResult(
                success=False,
                chat_id=target_chat,
                error=data.get("description", "Unknown Telegram API error"),
            )
        except Exception as exc:
            logger.error("Failed to send Telegram alert: %s", exc)
            return TelegramNotificationResult(
                success=False,
                chat_id=target_chat,
                error=str(exc),
            )
        finally:
            if not self._client:
                await client.aclose()

    async def update_call_card(
        self,
        chat_id: str | int,
        message_id: int,
        new_text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> TelegramNotificationResult:
        """Edits an existing Telegram call card (e.g. after takeover or status change)."""
        if self.bot_token == "MOCK_TELEGRAM_TOKEN" or not self.bot_token:
            logger.info("Mock Telegram message %d updated in chat %s", message_id, chat_id)
            return TelegramNotificationResult(
                success=True,
                chat_id=chat_id,
                message_id=message_id,
                action="update",
            )

        client = self._client or httpx.AsyncClient()
        try:
            url = f"{self._api_base}/editMessageText"
            body: dict[str, Any] = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "HTML",
            }
            if reply_markup is not None:
                body["reply_markup"] = reply_markup

            res = await client.post(url, json=body, timeout=5.0)
            data = res.json()
            return TelegramNotificationResult(
                success=bool(res.is_success and data.get("ok")),
                chat_id=chat_id,
                message_id=message_id,
                action="update",
                error=None if data.get("ok") else data.get("description"),
            )
        except Exception as exc:
            logger.error("Failed to edit Telegram message: %s", exc)
            return TelegramNotificationResult(
                success=False,
                chat_id=chat_id,
                message_id=message_id,
                action="update",
                error=str(exc),
            )
        finally:
            if not self._client:
                await client.aclose()

    async def send_call_summary(
        self,
        call_id: str,
        caller_name: str,
        summary_text: str,
        duration_seconds: int,
        chat_id: str | int | None = None,
    ) -> TelegramNotificationResult:
        """Sends a post-call summary recap card when a call terminates."""
        target_chat = chat_id or self.default_chat_id
        text = (
            f"📋 <b>Call Summary & Wrap-up</b>\n\n"
            f"👤 <b>Caller:</b> {caller_name}\n"
            f"⏱️ <b>Duration:</b> {duration_seconds}s\n"
            f"🆔 <code>{call_id}</code>\n\n"
            f"📝 <b>Key Takeaways:</b>\n{summary_text}"
        )

        if self.bot_token == "MOCK_TELEGRAM_TOKEN" or not self.bot_token:
            return TelegramNotificationResult(
                success=True,
                chat_id=target_chat,
                message_id=999002,
                action="summary",
            )

        client = self._client or httpx.AsyncClient()
        try:
            url = f"{self._api_base}/sendMessage"
            body = {
                "chat_id": target_chat,
                "text": text,
                "parse_mode": "HTML",
            }
            res = await client.post(url, json=body, timeout=5.0)
            data = res.json()
            return TelegramNotificationResult(
                success=bool(res.is_success and data.get("ok")),
                chat_id=target_chat,
                message_id=data.get("result", {}).get("message_id"),
                action="summary",
            )
        finally:
            if not self._client:
                await client.aclose()


class TelegramCallbackHandler:
    """Parses and handles interactive callback queries from Telegram buttons."""

    def __init__(
        self,
        handoff_manager: HandoffManager,
        notifier: TelegramCallNotifier,
    ) -> None:
        self.handoff_manager = handoff_manager
        self.notifier = notifier

    async def handle_callback(
        self,
        callback_data: str,
        chat_id: str | int,
        message_id: int,
        target_endpoint: str = "PJSIP/1002",
    ) -> dict[str, Any]:
        """Handles `handoff:<action>:<call_id>` callback queries."""
        parts = callback_data.split(":")
        if len(parts) < 3 or parts[0] != "handoff":
            return {"success": False, "message": "Invalid callback query format"}

        action_str = parts[1]
        call_id = parts[2]

        try:
            action = TelegramCallbackAction(action_str)
        except ValueError:
            return {"success": False, "message": f"Unknown callback action: {action_str}"}

        status_text = ""
        if action == TelegramCallbackAction.TAKE_CALL:
            res = await self.handoff_manager.take_call(
                call_id=call_id,
                target_endpoint=target_endpoint,
                reason="Telegram Button Tap",
            )
            status_text = (
                f"✅ <b>Call Bridged to Human</b>\n\n"
                f"📞 Softphone: <code>{target_endpoint}</code>\n"
                f"🆔 Call ID: <code>{call_id}</code>\n"
                f"<i>AI assistant muted and detached.</i>"
            )
        elif action == TelegramCallbackAction.KEEP_AI:
            res = await self.handoff_manager.keep_ai(
                call_id=call_id,
                reason="Telegram Keep AI Button",
            )
            status_text = (
                f"🤖 <b>AI Assistant Continuing Call</b>\n\n"
                f"🆔 Call ID: <code>{call_id}</code>\n"
                f"<i>Autonomous screening in progress.</i>"
            )
        elif action == TelegramCallbackAction.END_CALL:
            res = await self.handoff_manager.end_call(
                call_id=call_id,
                reason="Telegram Hangup Button",
            )
            status_text = (
                f"🛑 <b>Call Terminated by User</b>\n\n"
                f"🆔 Call ID: <code>{call_id}</code>\n"
                f"<i>Caller disconnected.</i>"
            )
        elif action == TelegramCallbackAction.RESUME_AI:
            res = await self.handoff_manager.resume_ai(
                call_id=call_id,
                reason="Telegram Resume AI Button",
            )
            status_text = (
                f"🔄 <b>Call Transferred Back to AI</b>\n\n🆔 Call ID: <code>{call_id}</code>"
            )

        # Update the original Telegram card in place
        await self.notifier.update_call_card(
            chat_id=chat_id,
            message_id=message_id,
            new_text=status_text,
            reply_markup={"inline_keyboard": []},
        )

        return {
            "success": res.success,
            "call_id": call_id,
            "action": action.value,
            "current_state": res.current_state.value,
            "message": res.message,
        }
