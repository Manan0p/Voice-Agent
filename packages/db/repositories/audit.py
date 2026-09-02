import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.audit import AgentAction


class ActionAuditRepository:
    """Repository recording and querying agent tool execution audit trails."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_action(
        self,
        tool_name: str,
        caller_id: str = "unknown",
        arguments: dict[str, Any] | None = None,
        success: bool = True,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        permission_level: str = "read_only",
        call_id: uuid.UUID | None = None,
    ) -> AgentAction:
        """Create and persist an audit record for an executed agent tool."""
        action = AgentAction(
            call_id=call_id,
            caller_id=caller_id,
            tool_name=tool_name,
            arguments=arguments,
            success=success,
            data=data,
            error=error,
            permission_level=permission_level,
        )
        self.session.add(action)
        await self.session.flush()
        return action

    async def get_actions_for_call(self, call_id: uuid.UUID) -> list[AgentAction]:
        """Fetch all audit events belonging to a specific call session."""
        stmt = (
            select(AgentAction)
            .where(AgentAction.call_id == call_id)
            .order_by(AgentAction.created_at)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_recent_actions(self, limit: int = 50) -> list[AgentAction]:
        """Fetch latest tool audit events across all calls."""
        stmt = select(AgentAction).order_by(desc(AgentAction.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
