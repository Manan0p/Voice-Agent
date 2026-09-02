import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.caller import Caller
from packages.db.session import get_async_session
from packages.schemas.common import PaginatedResponse
from packages.schemas.contacts import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
)

router = APIRouter(prefix="/api/contacts", tags=["Contacts"])


@router.get("", response_model=PaginatedResponse[ContactResponse])
async def list_contacts(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(
        default=None, description="Search query across name, phone, relationship, organization"
    ),
    relationship: str | None = Query(default=None),
) -> PaginatedResponse[ContactResponse]:
    """List all contacts with search and pagination."""
    stmt = select(Caller)
    count_stmt = select(func.count()).select_from(Caller)

    if q:
        search_filter = or_(
            Caller.name.ilike(f"%{q}%"),
            Caller.phone_number.ilike(f"%{q}%"),
            Caller.relationship.ilike(f"%{q}%"),
            Caller.organization.ilike(f"%{q}%"),
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    if relationship:
        stmt = stmt.where(Caller.relationship == relationship)
        count_stmt = count_stmt.where(Caller.relationship == relationship)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    stmt = stmt.order_by(desc(Caller.created_at)).limit(limit).offset(offset)
    res = await db.execute(stmt)
    contacts = list(res.scalars().all())

    return PaginatedResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[ContactResponse.model_validate(c) for c in contacts],
    )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> ContactResponse:
    """Create a new contact profile."""
    # Check if contact with phone already exists
    stmt = select(Caller).where(Caller.phone_number == payload.phone_number)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Contact with phone number '{payload.phone_number}' already exists",
        )

    contact = Caller(
        phone_number=payload.phone_number,
        name=payload.name,
        relationship=payload.relationship,
        trust_score=payload.trust_score,
        organization=payload.organization,
        language_preference=payload.language_preference,
        notes=payload.notes,
        is_blocked=payload.is_blocked,
    )
    db.add(contact)
    await db.flush()
    return ContactResponse.model_validate(contact)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> ContactResponse:
    """Retrieve contact by ID."""
    stmt = select(Caller).where(Caller.id == contact_id)
    res = await db.execute(stmt)
    contact = res.scalar_one_or_none()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Contact '{contact_id}' not found"
        )

    return ContactResponse.model_validate(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> ContactResponse:
    """Update contact profile details."""
    stmt = select(Caller).where(Caller.id == contact_id)
    res = await db.execute(stmt)
    contact = res.scalar_one_or_none()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Contact '{contact_id}' not found"
        )

    if payload.name is not None:
        contact.name = payload.name
    if payload.relationship is not None:
        contact.relationship = payload.relationship
    if payload.trust_score is not None:
        contact.trust_score = payload.trust_score
    if payload.organization is not None:
        contact.organization = payload.organization
    if payload.language_preference is not None:
        contact.language_preference = payload.language_preference
    if payload.notes is not None:
        contact.notes = payload.notes
    if payload.is_blocked is not None:
        contact.is_blocked = payload.is_blocked

    await db.flush()
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> Response:
    """Delete contact profile."""
    stmt = select(Caller).where(Caller.id == contact_id)
    res = await db.execute(stmt)
    contact = res.scalar_one_or_none()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Contact '{contact_id}' not found"
        )

    await db.delete(contact)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
