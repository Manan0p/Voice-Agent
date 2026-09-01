import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PermissionLevel(StrEnum):
    """Safety and permission tiers for agent tool execution."""

    READ_ONLY = "read_only"
    LOW_RISK_WRITE = "low_risk_write"
    HIGH_RISK_WRITE = "high_risk_write"
    USER_CONFIRMATION_REQUIRED = "user_confirmation_required"
    DENIED = "denied"


@dataclass
class ToolResult:
    """Output container for tool execution."""

    success: bool
    data: Any = None
    error: str | None = None
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY


@dataclass
class ToolAuditEvent:
    """Structured audit trail record for each tool invocation."""

    timestamp: float = field(default_factory=time.time)
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    caller_id: str = "unknown"
    success: bool = False
    data: Any = None
    error: str | None = None


class BaseTool(ABC):
    """Abstract interface for tools callable by the AI agent."""

    name: str
    description: str
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    args_schema: type[BaseModel] | None = None

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic."""
        ...

    def get_parameters_schema(self) -> dict[str, Any]:
        """Generate JSON schema for tool parameters."""
        if self.args_schema:
            schema = self.args_schema.model_json_schema()
            return {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            }
        return {"type": "object", "properties": {}}
