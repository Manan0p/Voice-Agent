"""FastAPI router for human handoff and live call intervention endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.agent.telephony.handoff import HandoffManager, get_handoff_manager
from packages.db.repositories.audit import ActionAuditRepository
from packages.db.session import get_async_session
from packages.schemas.common import StandardErrorResponse
from packages.schemas.handoff import (
    HandoffRequest,
    HandoffResponse,
    HandoffStatus,
)
from packages.shared.logging import get_logger

logger = get_logger("apps.api.routes.handoff")

router = APIRouter(prefix="/api/calls/{call_id}/handoff", tags=["Human Handoff"])


@router.post(
    "/take",
    response_model=HandoffResponse,
    summary="Take over active call",
    description="Immediately cuts off AI speech and bridges the caller to the user's phone or softphone.",
    responses={404: {"model": StandardErrorResponse}},
)
async def take_call(
    call_id: str,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    handoff_mgr: Annotated[HandoffManager, Depends(get_handoff_manager)],
    request: HandoffRequest | None = None,
) -> HandoffResponse:
    target_endpoint = request.target_endpoint if request else "PJSIP/1002"
    reason = request.reason if request else "User manual takeover"

    resp = await handoff_mgr.take_call(
        call_id=call_id,
        target_endpoint=target_endpoint or "PJSIP/1002",
        reason=reason,
    )

    # Record action audit
    try:
        audit_repo = ActionAuditRepository(db)
        await audit_repo.record_action(
            tool_name="handoff_take_call",
            arguments={"target_endpoint": target_endpoint, "reason": reason},
            result={"status": "success", "bridge_id": resp.bridge_id},
            permission_level="HIGH_RISK_WRITE",
            caller_id=call_id,
            execution_status="success",
        )
    except Exception as e:
        logger.warning("Failed to record handoff audit log: %s", e)

    return resp


@router.post(
    "/keep-ai",
    response_model=HandoffResponse,
    summary="Keep AI handling active",
    description="Dismisses escalation alert and keeps autonomous AI flow active.",
)
async def keep_ai(
    call_id: str,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    handoff_mgr: Annotated[HandoffManager, Depends(get_handoff_manager)],
    request: HandoffRequest | None = None,
) -> HandoffResponse:
    reason = request.reason if request else "User acknowledged escalation and delegated to AI"
    resp = await handoff_mgr.keep_ai(call_id=call_id, reason=reason)

    try:
        audit_repo = ActionAuditRepository(db)
        await audit_repo.record_action(
            tool_name="handoff_keep_ai",
            arguments={"reason": reason},
            result={"status": "success"},
            permission_level="LOW_RISK_WRITE",
            caller_id=call_id,
            execution_status="success",
        )
    except Exception as e:
        logger.warning("Failed to record handoff audit log: %s", e)

    return resp


@router.post(
    "/end",
    response_model=HandoffResponse,
    summary="Terminate call",
    description="Forces immediate call termination and disconnects all parties.",
)
async def end_call(
    call_id: str,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    handoff_mgr: Annotated[HandoffManager, Depends(get_handoff_manager)],
    request: HandoffRequest | None = None,
) -> HandoffResponse:
    reason = request.reason if request else "Call terminated by user"
    resp = await handoff_mgr.end_call(call_id=call_id, reason=reason)

    try:
        audit_repo = ActionAuditRepository(db)
        await audit_repo.record_action(
            tool_name="handoff_end_call",
            arguments={"reason": reason},
            result={"status": "success"},
            permission_level="HIGH_RISK_WRITE",
            caller_id=call_id,
            execution_status="success",
        )
    except Exception as e:
        logger.warning("Failed to record handoff audit log: %s", e)

    return resp


@router.post(
    "/resume-ai",
    response_model=HandoffResponse,
    summary="Resume AI handling",
    description="Transfers call from human back to the autonomous AI assistant.",
)
async def resume_ai(
    call_id: str,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    handoff_mgr: Annotated[HandoffManager, Depends(get_handoff_manager)],
    request: HandoffRequest | None = None,
) -> HandoffResponse:
    reason = request.reason if request else "Human transferred call back to AI assistant"
    resp = await handoff_mgr.resume_ai(call_id=call_id, reason=reason)

    try:
        audit_repo = ActionAuditRepository(db)
        await audit_repo.record_action(
            tool_name="handoff_resume_ai",
            arguments={"reason": reason},
            result={"status": "success"},
            permission_level="LOW_RISK_WRITE",
            caller_id=call_id,
            execution_status="success",
        )
    except Exception as e:
        logger.warning("Failed to record handoff audit log: %s", e)

    return resp


@router.get(
    "/status",
    response_model=HandoffStatus,
    summary="Get handoff status",
    description="Retrieves live diagnostics and handoff state for a call.",
)
async def get_status(
    call_id: str,
    handoff_mgr: Annotated[HandoffManager, Depends(get_handoff_manager)],
) -> HandoffStatus:
    return handoff_mgr.get_status(call_id=call_id)
