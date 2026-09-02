import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.caller import Caller
from packages.db.models.message import Message
from packages.db.session import get_async_session
from packages.schemas.common import PaginatedResponse
from packages.schemas.messages import (
    MessageCreate,
    MessageResponse,
    MessageUpdate,
)

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.get("", response_model=PaginatedResponse[MessageResponse])
async def list_messages(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_read: bool | None = Query(default=None),
    urgency: str | None = Query(default=None),
    category: str | None = Query(default=None),
    phone_number: str | None = Query(default=None),
) -> PaginatedResponse[MessageResponse]:
    """List all caller voicemails and messages with filters."""
    stmt = select(Message)
    count_stmt = select(func.count()).select_from(Message)

    if is_read is not None:
        stmt = stmt.where(Message.is_read == is_read)
        count_stmt = count_stmt.where(Message.is_read == is_read)
    if urgency:
        stmt = stmt.where(Message.urgency == urgency)
        count_stmt = count_stmt.where(Message.urgency == urgency)
    if category:
        stmt = stmt.where(Message.category == category)
        count_stmt = count_stmt.where(Message.category == category)
    if phone_number:
        stmt = stmt.where(Message.phone_number == phone_number)
        count_stmt = count_stmt.where(Message.phone_number == phone_number)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    stmt = stmt.order_by(desc(Message.created_at)).limit(limit).offset(offset)
    res = await db.execute(stmt)
    messages = list(res.scalars().all())

    return PaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[MessageResponse.model_validate(m) for m in messages],
    )


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: MessageCreate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> MessageResponse:
    """Record a new caller message/voicemail."""
    caller_id = None
    if payload.phone_number:
        caller_stmt = select(Caller).where(Caller.phone_number == payload.phone_number)
        caller_res = await db.execute(caller_stmt)
        caller = caller_res.scalar_one_or_none()
        if not caller:
            caller = Caller(phone_number=payload.phone_number, name=payload.caller_name)
            db.add(caller)
            await db.flush()
        caller_id = caller.id

    msg = Message(
        caller_id=caller_id,
        call_id=payload.call_id,
        caller_name=payload.caller_name,
        phone_number=payload.phone_number,
        message_content=payload.message,
        urgency=payload.urgency,
        category=payload.category,
        is_read=False,
    )
    db.add(msg)
    await db.flush()
    return MessageResponse.model_validate(msg)


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> MessageResponse:
    """Retrieve an individual voicemail message."""
    stmt = select(Message).where(Message.id == message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()

    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Message '{message_id}' not found"
        )

    return MessageResponse.model_validate(msg)


@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: uuid.UUID,
    payload: MessageUpdate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> MessageResponse:
    """Update message read status, urgency, or category."""
    stmt = select(Message).where(Message.id == message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()

    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Message '{message_id}' not found"
        )

    if payload.is_read is not None:
        msg.is_read = payload.is_read
    if payload.urgency is not None:
        msg.urgency = payload.urgency
    if payload.category is not None:
        msg.category = payload.category

    await db.flush()
    return MessageResponse.model_validate(msg)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> Response:
    """Delete a voicemail record."""
    stmt = select(Message).where(Message.id == message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()

    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Message '{message_id}' not found"
        )

    await db.delete(msg)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
