from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession

from apps.agent.telephony.state_machine import TelephonyCallSession
from apps.agent.telephony.twilio_bridge import TwilioMediaStreamBridge
from packages.db.repositories.caller_memory import CallerMemoryRepository
from packages.db.session import get_async_session
from packages.shared.logging import get_logger

logger = get_logger("apps.api.routes.telephony")
router = APIRouter(prefix="/api/telephony", tags=["Telephony"])


@router.post("/twilio/incoming")
async def twilio_incoming_call_webhook(
    request: Request,
    From: str = Form(default="unknown"),
    To: str = Form(default="unknown"),
    CallSid: str = Form(default="unknown_call"),
) -> Response:
    """Twilio Voice Webhook called on incoming phone call. Returns TwiML Media Stream instructions."""
    # Determine websocket host
    host = request.headers.get("host", "localhost:8000")
    ws_scheme = "wss" if request.url.scheme == "https" else "ws"
    stream_url = f"{ws_scheme}://{host}/api/telephony/twilio/stream"

    logger.info("Incoming phone call received from %s to %s (CallSid=%s)", From, To, CallSid)

    twiml = TwilioMediaStreamBridge.generate_twiml(
        stream_url=stream_url,
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/status")
async def twilio_call_status_callback(
    CallSid: str = Form(default="unknown"),
    CallStatus: str = Form(default="completed"),
    CallDuration: str | None = Form(default=None),
) -> dict[str, str]:
    """Twilio Call Status Callback."""
    logger.info(
        "Twilio Call status updated: CallSid=%s, Status=%s, Duration=%s",
        CallSid,
        CallStatus,
        CallDuration,
    )
    return {"status": "received", "call_sid": CallSid}


@router.websocket("/twilio/stream")
async def twilio_media_stream_websocket(
    websocket: WebSocket,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    """Bidirectional WebSocket streaming audio between Twilio and the AI Voice Agent."""
    await websocket.accept()
    logger.info("Twilio media stream WebSocket connection accepted")

    session = TelephonyCallSession(call_sid="pending")
    bridge = TwilioMediaStreamBridge(session=session)
    caller_repo = CallerMemoryRepository(db)

    db_call = None

    try:
        while True:
            raw_msg = await websocket.receive_text()
            event = bridge.handle_inbound_message(raw_msg)

            event_type = event.get("event")

            if event_type == "start":
                caller_phone = event.get("caller_phone", "unknown")
                stream_sid = event.get("stream_sid", "unknown")

                # Create active DB call record
                try:
                    db_call = await caller_repo.create_call(
                        phone=caller_phone,
                        status="active",
                    )
                    await db.commit()
                except Exception as e:
                    logger.warning("Could not persist call session in DB: %s", e)

                # Send initial greeting audio to caller if stream started
                greeting_frames = bridge.create_media_frames(
                    pcm_or_mulaw_audio=b"\x00" * 320,  # Telephony silence framing
                    stream_sid=stream_sid,
                    is_already_mulaw=True,
                )
                for frame in greeting_frames:
                    await websocket.send_text(frame)

            elif event_type == "media":
                # Inbound audio received
                stream_sid = event.get("stream_sid")
                pcm_bytes = event.get("pcm16_bytes")

                # Echo back packet response or bridge to VAD/STT
                # In production, frames are passed into FasterWhisperSTTService
                if stream_sid and pcm_bytes:
                    pass

            elif event_type == "stop":
                logger.info("Twilio stream stopped for call: %s", session.call_sid)
                if db_call:
                    await caller_repo.end_call(
                        call_id=db_call.id,
                        duration_sec=session.duration_sec,
                        status="completed",
                    )
                    await db.commit()
                break

    except WebSocketDisconnect:
        logger.info("Twilio WebSocket disconnected: CallSid=%s", session.call_sid)
    except Exception as e:
        logger.error("Error in Twilio Media Stream WebSocket: %s", e, exc_info=True)
    finally:
        session.complete()
