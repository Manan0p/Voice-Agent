"""Pydantic schemas for Asterisk REST Interface (ARI) events and channel data."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AsteriskCallerID(BaseModel):
    """Caller ID information from Asterisk."""

    name: str = ""
    number: str = ""


class AsteriskChannel(BaseModel):
    """Asterisk channel representation."""

    id: str
    name: str
    state: str = "Down"
    caller: AsteriskCallerID = Field(default_factory=AsteriskCallerID)
    connected: AsteriskCallerID = Field(default_factory=AsteriskCallerID)
    creationtime: datetime | str | None = None
    language: str = "en"
    dialplan: dict[str, Any] = Field(default_factory=dict)


class AsteriskBridge(BaseModel):
    """Asterisk bridge representation."""

    id: str
    technology: str = "simple_bridge"
    bridge_type: str = "mixing"
    bridge_class: str = "default"
    creator: str = ""
    name: str = ""
    channels: list[str] = Field(default_factory=list)


class ARIEvent(BaseModel):
    """Base model for Asterisk ARI WebSocket events."""

    type: str
    application: str = ""
    timestamp: datetime | str | None = None
    asterisk_id: str | None = None


class StasisStartEvent(ARIEvent):
    """Event sent when a channel enters a Stasis application."""

    type: str = "StasisStart"
    channel: AsteriskChannel
    args: list[str] = Field(default_factory=list)
    replace_channel: AsteriskChannel | None = None


class StasisEndEvent(ARIEvent):
    """Event sent when a channel leaves a Stasis application."""

    type: str = "StasisEnd"
    channel: AsteriskChannel


class ChannelStateChangeEvent(ARIEvent):
    """Event sent when a channel changes state."""

    type: str = "ChannelStateChange"
    channel: AsteriskChannel


class ChannelHangupRequestEvent(ARIEvent):
    """Event sent when a hangup is requested on a channel."""

    type: str = "ChannelHangupRequest"
    channel: AsteriskChannel
    cause: int = 0
