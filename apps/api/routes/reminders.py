import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.reminder import Reminder
from packages.db.session import get_async_session
from packages.schemas.reminders import (
    ReminderCreate,
    ReminderResponse,
)

router = APIRouter(prefix="/api/reminders", tags=["Reminders"])


@router.get("", response_model=list[ReminderResponse])
async def list_reminders(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    is_completed: bool | None = Query(default=None),
) -> list[ReminderResponse]:
    """List all scheduled task and callback reminders."""
    stmt = select(Reminder)
    if is_completed is not None:
        stmt = stmt.where(Reminder.is_completed == is_completed)

    stmt = stmt.order_by(desc(Reminder.created_at))
    res = await db.execute(stmt)
    reminders = list(res.scalars().all())
    return [ReminderResponse.model_validate(r) for r in reminders]


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> ReminderResponse:
    """Create a new task reminder."""
    reminder = Reminder(
        title=payload.title,
        description=payload.description,
        due_at=payload.due_at,
        caller_id=payload.caller_id,
        is_completed=False,
    )
    db.add(reminder)
    await db.flush()
    return ReminderResponse.model_validate(reminder)


@router.patch("/{reminder_id}/complete", response_model=ReminderResponse)
async def toggle_reminder_complete(
    reminder_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    completed: bool = Query(default=True),
) -> ReminderResponse:
    """Mark reminder completed or active."""
    stmt = select(Reminder).where(Reminder.id == reminder_id)
    res = await db.execute(stmt)
    reminder = res.scalar_one_or_none()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Reminder '{reminder_id}' not found"
        )

    reminder.is_completed = completed
    await db.flush()
    return ReminderResponse.model_validate(reminder)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> Response:
    """Delete a reminder."""
    stmt = select(Reminder).where(Reminder.id == reminder_id)
    res = await db.execute(stmt)
    reminder = res.scalar_one_or_none()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Reminder '{reminder_id}' not found"
        )

    await db.delete(reminder)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
