import time
from typing import Any

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolAuditEvent, ToolResult
from apps.agent.tools.builtin import GetCurrentTimeTool, SaveCallerMessageTool
from apps.agent.tools.contacts import GetCallerHistoryTool, GetContactTool
from apps.agent.tools.knowledge import SearchKnowledgeTool
from apps.agent.tools.notification import NotifyUserTool
from apps.agent.tools.telephony import EndCallTool, TransferCallTool
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.tools.registry")


class ToolRegistry:
    """Registry maintaining available agent tools, permission gates, and execution audit logging."""

    def __init__(self, register_defaults: bool = True) -> None:
        self._tools: dict[str, BaseTool] = {}
        self.audit_log: list[ToolAuditEvent] = []

        if register_defaults:
            self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the standard suite of 7+ core agent tools."""
        self.register(GetContactTool())
        self.register(GetCallerHistoryTool())
        self.register(SaveCallerMessageTool(name="save_message"))
        self.register(SaveCallerMessageTool(name="save_caller_message"))
        self.register(SearchKnowledgeTool())
        self.register(NotifyUserTool())
        self.register(TransferCallTool())
        self.register(EndCallTool())
        self.register(GetCurrentTimeTool())

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        self._tools[tool.name] = tool
        logger.debug("Registered tool: '%s' (permission=%s)", tool.name, tool.permission_level)

    def get(self, name: str) -> BaseTool | None:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return schema list for all registered tools formatted for LLM function calling."""
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
        caller_id: str = "unknown",
    ) -> ToolResult:
        """Execute a tool with permission enforcement, error handling, and audit logging."""
        tool = self.get(name)
        start_ts = time.time()

        # Handle hallucinated/unknown tool call
        if not tool:
            err_msg = f"Tool '{name}' is not recognized or available."
            logger.warning("Hallucinated tool execution attempted: %s", name)

            audit = ToolAuditEvent(
                timestamp=start_ts,
                tool_name=name,
                arguments=arguments,
                caller_id=caller_id,
                success=False,
                data=None,
                error=err_msg,
            )
            self.audit_log.append(audit)

            return ToolResult(
                success=False,
                error=err_msg,
                permission_level=PermissionLevel.DENIED,
            )

        # Permission check
        if tool.permission_level == PermissionLevel.DENIED:
            err_msg = f"Tool '{name}' permission is denied by security policy."
            logger.warning("Denied tool execution attempted: %s", name)

            audit = ToolAuditEvent(
                timestamp=start_ts,
                tool_name=name,
                arguments=arguments,
                caller_id=caller_id,
                success=False,
                data=None,
                error=err_msg,
            )
            self.audit_log.append(audit)

            return ToolResult(
                success=False,
                error=err_msg,
                permission_level=PermissionLevel.DENIED,
            )

        # Validate arguments with schema if defined
        if tool.args_schema:
            try:
                # Merge internal caller_id into kwargs
                kwargs_to_validate = dict(arguments)
                tool.args_schema(**kwargs_to_validate)
            except Exception as e:
                err_msg = f"Invalid arguments for tool '{name}': {str(e)}"
                logger.error("Argument validation failed for '%s': %s", name, str(e))

                audit = ToolAuditEvent(
                    timestamp=start_ts,
                    tool_name=name,
                    arguments=arguments,
                    caller_id=caller_id,
                    success=False,
                    data=None,
                    error=err_msg,
                )
                self.audit_log.append(audit)

                return ToolResult(
                    success=False,
                    error=err_msg,
                    permission_level=tool.permission_level,
                )

        # Execute tool
        try:
            exec_kwargs = dict(arguments)
            exec_kwargs["_caller_id"] = caller_id
            result = await tool.execute(**exec_kwargs)

            audit = ToolAuditEvent(
                timestamp=start_ts,
                tool_name=name,
                arguments=arguments,
                caller_id=caller_id,
                success=result.success,
                data=result.data,
                error=result.error,
            )
            self.audit_log.append(audit)

            logger.info("Tool '%s' executed: success=%s", name, result.success)
            return result

        except Exception as e:
            err_msg = f"Tool execution failed for '{name}': {str(e)}"
            logger.error(err_msg, exc_info=True)

            audit = ToolAuditEvent(
                timestamp=start_ts,
                tool_name=name,
                arguments=arguments,
                caller_id=caller_id,
                success=False,
                data=None,
                error=err_msg,
            )
            self.audit_log.append(audit)

            return ToolResult(
                success=False,
                error=err_msg,
                permission_level=tool.permission_level,
            )
