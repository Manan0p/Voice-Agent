from typing import Any

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolResult
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.tools.registry")


class ToolRegistry:
    """Central registry and executor for Agent tools with permission gating and audit logging."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._audit_log: list[dict[str, Any]] = []

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s (permission: %s)", tool.name, tool.permission_level)

    def get(self, name: str) -> BaseTool | None:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI/Gemini compatible function declaration list."""
        schemas = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.get_parameters_schema(),
                }
            )
        return schemas

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        caller_id: str | None = None,
    ) -> ToolResult:
        """Execute tool with permission gating and audit logging."""
        tool = self._tools.get(name)
        if not tool:
            err = f"Tool '{name}' not found in registry."
            logger.warning(err)
            return ToolResult(success=False, error=err)

        if tool.permission_level == PermissionLevel.DENIED:
            err = f"Execution of tool '{name}' is denied by policy."
            logger.warning(err)
            return ToolResult(
                success=False,
                error=err,
                permission_level=PermissionLevel.DENIED,
            )

        logger.info(
            "Executing tool '%s' with args %s (caller: %s)",
            name,
            arguments,
            caller_id,
        )

        try:
            result = await tool.execute(**arguments)
            self._audit_log.append(
                {
                    "tool": name,
                    "arguments": arguments,
                    "caller_id": caller_id,
                    "success": result.success,
                    "error": result.error,
                }
            )
            return result
        except Exception as e:
            logger.exception("Error executing tool '%s': %s", name, str(e))
            return ToolResult(success=False, error=str(e))

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return audit history of tool executions."""
        return self._audit_log
