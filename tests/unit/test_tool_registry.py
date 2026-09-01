import pytest

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolResult
from apps.agent.tools.builtin import GetCurrentTimeTool, SaveCallerMessageTool
from apps.agent.tools.registry import ToolRegistry


class DeniedTool(BaseTool):
    name = "denied_tool"
    description = "Test tool with denied permission"
    permission_level = PermissionLevel.DENIED

    async def execute(self, **kwargs: object) -> ToolResult:
        return ToolResult(success=True, data="Should not run")


@pytest.mark.asyncio
async def test_builtin_tools_execution() -> None:
    """Verify execution of built-in tools."""
    registry = ToolRegistry()
    time_tool = GetCurrentTimeTool()
    msg_tool = SaveCallerMessageTool()

    registry.register(time_tool)
    registry.register(msg_tool)

    # Test time tool
    time_res = await registry.execute("get_current_time", {})
    assert time_res.success is True
    assert "formatted" in time_res.data

    # Test message tool
    msg_res = await registry.execute(
        "save_caller_message",
        {"caller_name": "Rahul", "message_content": "Please call back by 6 PM."},
    )
    assert msg_res.success is True
    assert msg_res.data["caller_name"] == "Rahul"


@pytest.mark.asyncio
async def test_permission_denied_tool() -> None:
    """Verify that tools with DENIED permission level are blocked."""
    registry = ToolRegistry()
    registry.register(DeniedTool())

    res = await registry.execute("denied_tool", {})
    assert res.success is False
    assert res.permission_level == PermissionLevel.DENIED


@pytest.mark.asyncio
async def test_unknown_tool_handling() -> None:
    """Verify graceful handling when an unknown tool is called."""
    registry = ToolRegistry()
    res = await registry.execute("non_existent_tool", {})
    assert res.success is False
    assert "not recognized" in (res.error or "") or "not found" in (res.error or "")


def test_schema_generation() -> None:
    """Verify tool JSON schema formatting."""
    registry = ToolRegistry(register_defaults=False)
    registry.register(GetCurrentTimeTool())
    registry.register(SaveCallerMessageTool())

    schemas = registry.get_schemas()
    assert len(schemas) == 2
    names = [s["name"] for s in schemas]
    assert "get_current_time" in names
    assert "save_caller_message" in names
