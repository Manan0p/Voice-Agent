import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.db.models.call import Call
from packages.db.models.caller import Caller
from packages.db.models.message import Message


class CallerMemoryRepository:
    """Repository managing caller profiles, multi-turn history, call sessions, and voicemails."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_caller_by_phone(self, phone: str) -> Caller | None:
        """Fetch caller profile by phone number."""
        stmt = select(Caller).where(Caller.phone_number == phone)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_or_create_caller(
        self,
        phone: str,
        name: str | None = None,
        relationship: str = "unknown",
        trust_score: float = 0.5,
        organization: str | None = None,
    ) -> Caller:
        """Retrieve existing caller or create a new caller record."""
        caller = await self.get_caller_by_phone(phone)
        if not caller:
            caller = Caller(
                phone_number=phone,
                name=name,
                relationship=relationship,
                trust_score=trust_score,
                organization=organization,
            )
            self.session.add(caller)
            await self.session.flush()
        return caller

    async def update_caller(
        self,
        phone: str,
        name: str | None = None,
        relationship: str | None = None,
        trust_score: float | None = None,
        organization: str | None = None,
        notes: str | None = None,
    ) -> Caller | None:
        """Update fields on an existing caller profile."""
        caller = await self.get_caller_by_phone(phone)
        if not caller:
            return None

        if name is not None:
            caller.name = name
        if relationship is not None:
            caller.relationship = relationship
        if trust_score is not None:
            caller.trust_score = trust_score
        if organization is not None:
            caller.organization = organization
        if notes is not None:
            caller.notes = notes

        await self.session.flush()
        return caller

    async def create_call(
        self,
        phone: str,
        status: str = "active",
        intent: str | None = None,
        urgency: str | None = None,
    ) -> Call:
        """Create a new Call session record."""
        caller = await self.get_or_create_caller(phone=phone)
        call = Call(
            caller_id=caller.id,
            phone_number=phone,
            status=status,
            start_time=datetime.now(UTC),
            intent=intent,
            urgency=urgency,
        )
        self.session.add(call)
        await self.session.flush()
        return call

    async def end_call(
        self,
        call_id: uuid.UUID,
        duration_sec: float,
        summary: str | None = None,
        transcript: list[dict[str, Any]] | None = None,
        status: str = "completed",
    ) -> Call | None:
        """Mark a Call session as completed and attach summary and transcripts."""
        stmt = select(Call).where(Call.id == call_id)
        res = await self.session.execute(stmt)
        call = res.scalar_one_or_none()
        if not call:
            return None

        call.end_time = datetime.now(UTC)
        call.duration_sec = duration_sec
        call.summary = summary
        call.transcript = transcript
        call.status = status

        await self.session.flush()
        return call

    async def save_message(
        self,
        caller_name: str,
        message: str,
        phone_number: str | None = None,
        urgency: str = "normal",
        category: str = "general",
        call_id: uuid.UUID | None = None,
    ) -> Message:
        """Persist a structured caller voicemail/message."""
        caller_id = None
        if phone_number:
            caller = await self.get_or_create_caller(phone=phone_number, name=caller_name)
            caller_id = caller.id

        msg = Message(
            caller_id=caller_id,
            call_id=call_id,
            caller_name=caller_name,
            phone_number=phone_number,
            message_content=message,
            urgency=urgency,
            category=category,
            is_read=False,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_caller_history(
        self,
        phone: str,
        limit: int = 10,
    ) -> list[Call]:
        """Fetch past call history records for a caller."""
        stmt = (
            select(Call)
            .where(Call.phone_number == phone)
            .order_by(desc(Call.start_time))
            .limit(limit)
            .options(selectinload(Call.messages))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_unread_messages(self, limit: int = 50) -> list[Message]:
        """Fetch all unread caller messages."""
        stmt = (
            select(Message)
            .where(Message.is_read.is_(False))
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
