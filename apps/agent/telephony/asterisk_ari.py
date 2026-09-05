"""Asterisk REST Interface (ARI) client for asynchronous call management and event handling."""

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import aiohttp

from packages.schemas.asterisk import (
    ARIEvent,
    AsteriskBridge,
    AsteriskChannel,
    ChannelHangupRequestEvent,
    ChannelStateChangeEvent,
    StasisEndEvent,
    StasisStartEvent,
)

logger = logging.getLogger("voice_agent.telephony.asterisk_ari")


class AsteriskARIClient:
    """Asynchronous client for Asterisk REST Interface (ARI).

    Provides REST methods for channel/bridge lifecycle management and
    a WebSocket event listener for Stasis applications.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8088",
        username: str = "voice_agent",
        password: str = "agent_secret_pass",
        app_name: str = "voice_agent_app",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.app_name = app_name

        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._running = False
        self._listen_task: asyncio.Task[None] | None = None

        # Event callback registries: event_type -> list of async handlers
        self._handlers: dict[str, list[Callable[[ARIEvent], Coroutine[Any, Any, None]]]] = {
            "StasisStart": [],
            "StasisEnd": [],
            "ChannelStateChange": [],
            "ChannelHangupRequest": [],
        }

        # Active channels tracking: channel_id -> AsteriskChannel
        self.active_channels: dict[str, AsteriskChannel] = {}

    @property
    def auth(self) -> aiohttp.BasicAuth:
        """HTTP Basic Auth credential."""
        return aiohttp.BasicAuth(login=self.username, password=self.password)

    async def start(self) -> None:
        """Initialize the HTTP session and start the ARI WebSocket listener."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(auth=self.auth)
        self._running = True
        self._listen_task = asyncio.create_task(self._event_loop())
        logger.info(
            "Asterisk ARI Client started for app '%s' on %s",
            self.app_name,
            self.base_url,
        )

    async def stop(self) -> None:
        """Stop the WebSocket listener and close connections."""
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("Asterisk ARI Client stopped.")

    def on(self, event_type: str, handler: Callable[[Any], Coroutine[Any, Any, None]]) -> None:
        """Register an async callback for a specific ARI event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def _event_loop(self) -> None:
        """Connect to Asterisk ARI WebSocket and process incoming events."""
        ws_url = f"{self.base_url.replace('http://', 'ws://').replace('https://', 'wss://')}/ari/events?app={self.app_name}&api_key={self.username}:{self.password}"

        while self._running:
            try:
                if self._session is None or self._session.closed:
                    self._session = aiohttp.ClientSession(auth=self.auth)

                async with self._session.ws_connect(ws_url) as ws:
                    self._ws = ws
                    logger.info("Connected to Asterisk ARI WebSocket.")

                    async for msg in ws:
                        if not self._running:
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._dispatch_raw_event(msg.data)
                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            logger.warning("Asterisk ARI WebSocket closed: %s", msg.data)
                            break
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not self._running:
                    break
                logger.warning(
                    "Asterisk ARI connection error (%s). Reconnecting in 2s...",
                    exc,
                )
                await asyncio.sleep(2.0)

    async def _dispatch_raw_event(self, raw_data: str) -> None:
        """Parse raw JSON string into typed ARIEvent and dispatch to callbacks."""
        try:
            data = json.loads(raw_data)
            event_type = data.get("type", "")

            event: ARIEvent
            if event_type == "StasisStart":
                event = StasisStartEvent.model_validate(data)
                self.active_channels[event.channel.id] = event.channel
            elif event_type == "StasisEnd":
                event = StasisEndEvent.model_validate(data)
                self.active_channels.pop(event.channel.id, None)
            elif event_type == "ChannelStateChange":
                event = ChannelStateChangeEvent.model_validate(data)
                if event.channel.id in self.active_channels:
                    self.active_channels[event.channel.id] = event.channel
            elif event_type == "ChannelHangupRequest":
                event = ChannelHangupRequestEvent.model_validate(data)
            else:
                event = ARIEvent.model_validate(data)

            # Invoke registered callbacks
            handlers = self._handlers.get(event_type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as h_err:
                    logger.error(
                        "Error in ARI event handler for %s: %s",
                        event_type,
                        h_err,
                        exc_info=True,
                    )

        except Exception as exc:
            logger.error("Failed to parse ARI event: %s (%s)", raw_data, exc)

    # ==========================================
    # REST Channel Operations
    # ==========================================

    async def answer_channel(self, channel_id: str) -> bool:
        """Answer an active channel in Stasis."""
        if not self._session or self._session.closed:
            return False
        url = f"{self.base_url}/ari/channels/{channel_id}/answer"
        async with self._session.post(url) as resp:
            if resp.status in (200, 204):
                logger.info("Answered channel %s", channel_id)
                return True
            logger.error("Failed to answer channel %s: HTTP %s", channel_id, resp.status)
            return False

    async def hangup_channel(self, channel_id: str, reason: str = "normal") -> bool:
        """Hang up an active channel."""
        if not self._session or self._session.closed:
            return False
        url = f"{self.base_url}/ari/channels/{channel_id}"
        params = {"reason": reason}
        async with self._session.delete(url, params=params) as resp:
            if resp.status in (200, 204):
                self.active_channels.pop(channel_id, None)
                logger.info("Hung up channel %s (reason=%s)", channel_id, reason)
                return True
            logger.error("Failed to hangup channel %s: HTTP %s", channel_id, resp.status)
            return False

    async def play_media(self, channel_id: str, media_uri: str) -> dict[str, Any] | None:
        """Play audio media to a channel (e.g. 'sound:hello-world')."""
        if not self._session or self._session.closed:
            return None
        url = f"{self.base_url}/ari/channels/{channel_id}/play"
        params = {"media": media_uri}
        async with self._session.post(url, params=params) as resp:
            if resp.status in (200, 201):
                return await resp.json()
            logger.error(
                "Failed to play media %s on %s: HTTP %s", media_uri, channel_id, resp.status
            )
            return None

    async def create_bridge(
        self, bridge_type: str = "mixing", name: str = "voice_agent_bridge"
    ) -> AsteriskBridge | None:
        """Create a new Asterisk mixing or holding bridge."""
        if not self._session or self._session.closed:
            return None
        url = f"{self.base_url}/ari/bridges"
        params = {"type": bridge_type, "name": name}
        async with self._session.post(url, params=params) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return AsteriskBridge.model_validate(data)
            logger.error("Failed to create bridge: HTTP %s", resp.status)
            return None

    async def add_channel_to_bridge(self, bridge_id: str, channel_id: str) -> bool:
        """Add an active channel to an existing bridge."""
        if not self._session or self._session.closed:
            return False
        url = f"{self.base_url}/ari/bridges/{bridge_id}/addChannel"
        params = {"channel": channel_id}
        async with self._session.post(url, params=params) as resp:
            if resp.status in (200, 204):
                logger.info("Added channel %s to bridge %s", channel_id, bridge_id)
                return True
            logger.error(
                "Failed to add channel %s to bridge %s: HTTP %s",
                channel_id,
                bridge_id,
                resp.status,
            )
            return False

    async def remove_channel_from_bridge(self, bridge_id: str, channel_id: str) -> bool:
        """Remove a channel from a bridge."""
        if not self._session or self._session.closed:
            return False
        url = f"{self.base_url}/ari/bridges/{bridge_id}/removeChannel"
        params = {"channel": channel_id}
        async with self._session.post(url, params=params) as resp:
            if resp.status in (200, 204):
                logger.info("Removed channel %s from bridge %s", channel_id, bridge_id)
                return True
            return False

    async def external_media(
        self,
        external_host: str,
        audio_format: str = "slin16",
        direction: str = "both",
    ) -> AsteriskChannel | None:
        """Create an external media channel to stream real-time audio over RTP/Unicast."""
        if not self._session or self._session.closed:
            return None
        url = f"{self.base_url}/ari/channels/externalMedia"
        params = {
            "app": self.app_name,
            "external_host": external_host,
            "format": audio_format,
            "direction": direction,
        }
        async with self._session.post(url, params=params) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                return AsteriskChannel.model_validate(data)
            logger.error("Failed to create external media channel: HTTP %s", resp.status)
            return None
