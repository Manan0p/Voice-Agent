import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.db.models.call import Call
from packages.db.models.caller import Caller
from packages.db.session import get_async_session
from packages.schemas.calls import (
    CallCreate,
    CallDetailResponse,
    CallResponse,
    CallUpdate,
)
from packages.schemas.common import PaginatedResponse

router = APIRouter(prefix="/api/calls", tags=["Calls"])


@router.get("", response_model=PaginatedResponse[CallResponse])
async def list_calls(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    phone_number: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    intent: str | None = Query(default=None),
    urgency: str | None = Query(default=None),
) -> PaginatedResponse[CallResponse]:
    """List all call sessions with filtering and pagination."""
    stmt = select(Call)
    count_stmt = select(func.count()).select_from(Call)

    if phone_number:
        stmt = stmt.where(Call.phone_number == phone_number)
        count_stmt = count_stmt.where(Call.phone_number == phone_number)
    if status_filter:
        stmt = stmt.where(Call.status == status_filter)
        count_stmt = count_stmt.where(Call.status == status_filter)
    if intent:
        stmt = stmt.where(Call.intent == intent)
        count_stmt = count_stmt.where(Call.intent == intent)
    if urgency:
        stmt = stmt.where(Call.urgency == urgency)
        count_stmt = count_stmt.where(Call.urgency == urgency)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    stmt = stmt.order_by(desc(Call.start_time)).limit(limit).offset(offset)
    res = await db.execute(stmt)
    calls = list(res.scalars().all())

    return PaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[CallResponse.model_validate(c) for c in calls],
    )


@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    payload: CallCreate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> CallResponse:
    """Create a new Call record."""
    from datetime import UTC, datetime

    # Lookup or create caller
    caller_stmt = select(Caller).where(Caller.phone_number == payload.phone_number)
    caller_res = await db.execute(caller_stmt)
    caller = caller_res.scalar_one_or_none()

    if not caller:
        caller = Caller(phone_number=payload.phone_number)
        db.add(caller)
        await db.flush()

    call = Call(
        caller_id=caller.id,
        phone_number=payload.phone_number,
        status=payload.status,
        intent=payload.intent,
        urgency=payload.urgency,
        start_time=datetime.now(UTC),
    )
    db.add(call)
    await db.flush()
    return CallResponse.model_validate(call)


@router.get("/{call_id}", response_model=CallDetailResponse)
async def get_call(
    call_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> CallDetailResponse:
    """Get full details and transcripts for a specific call session."""
    stmt = (
        select(Call)
        .where(Call.id == call_id)
        .options(selectinload(Call.actions), selectinload(Call.messages))
    )
    res = await db.execute(stmt)
    call = res.scalar_one_or_none()

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Call '{call_id}' not found"
        )

    return CallDetailResponse.model_validate(call)


@router.patch("/{call_id}", response_model=CallDetailResponse)
async def update_call(
    call_id: uuid.UUID,
    payload: CallUpdate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> CallDetailResponse:
    """Update call details, transcripts, or status."""
    from datetime import UTC, datetime

    stmt = select(Call).where(Call.id == call_id)
    res = await db.execute(stmt)
    call = res.scalar_one_or_none()

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Call '{call_id}' not found"
        )

    if payload.status is not None:
        call.status = payload.status
        if payload.status in {"completed", "missed", "failed"} and not call.end_time:
            call.end_time = datetime.now(UTC)
    if payload.duration_sec is not None:
        call.duration_sec = payload.duration_sec
    if payload.intent is not None:
        call.intent = payload.intent
    if payload.urgency is not None:
        call.urgency = payload.urgency
    if payload.summary is not None:
        call.summary = payload.summary
    if payload.transcript is not None:
        call.transcript = payload.transcript

    await db.flush()
    return CallDetailResponse.model_validate(call)
