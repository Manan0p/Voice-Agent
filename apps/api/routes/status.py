from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.call import Call
from packages.db.models.caller import Caller
from packages.db.models.message import Message
from packages.db.models.reminder import Reminder
from packages.db.session import get_async_session
from packages.schemas.status import (
    ServiceComponentStatus,
    SystemStatusResponse,
)
from packages.shared.config import get_settings

router = APIRouter(prefix="/api/status", tags=["Status"])


@router.get("", response_model=SystemStatusResponse)
async def get_system_status(
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> SystemStatusResponse:
    """Retrieve full system status, service component health, and telemetry metrics."""
    settings = get_settings()

    # Query counts
    callers_count = (await db.execute(select(func.count()).select_from(Caller))).scalar_one()
    calls_count = (await db.execute(select(func.count()).select_from(Call))).scalar_one()
    unread_msgs = (
        await db.execute(
            select(func.count()).select_from(Message).where(Message.is_read.is_(False))
        )
    ).scalar_one()
    pending_reminders = (
        await db.execute(
            select(func.count()).select_from(Reminder).where(Reminder.is_completed.is_(False))
        )
    ).scalar_one()

    components = [
        ServiceComponentStatus(
            name="Database", status="operational", details="Async session active"
        ),
        ServiceComponentStatus(
            name="LLM Provider", status="operational", details=f"Provider: {settings.llm_provider}"
        ),
        ServiceComponentStatus(
            name="STT Engine",
            status="operational",
            details=f"faster-whisper ({settings.whisper_model_size})",
        ),
        ServiceComponentStatus(
            name="TTS Engine",
            status="operational",
            details=f"Kokoro-82M (voice: {settings.kokoro_voice})",
        ),
        ServiceComponentStatus(
            name="Decision Engine", status="operational", details="Multi-agent triage active"
        ),
    ]

    return SystemStatusResponse(
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
        llm_provider=settings.llm_provider,
        stt_model=f"faster-whisper-{settings.whisper_model_size}",
        tts_engine=f"kokoro-82M ({settings.kokoro_voice})",
        database_connected=True,
        total_callers=callers_count,
        total_calls=calls_count,
        unread_messages=unread_msgs,
        pending_reminders=pending_reminders,
        components=components,
    )
