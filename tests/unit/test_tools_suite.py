import pytest

from apps.agent.tools.base import PermissionLevel
from apps.agent.tools.builtin import SaveCallerMessageTool
from apps.agent.tools.contacts import GetCallerHistoryTool, GetContactTool
from apps.agent.tools.knowledge import SearchKnowledgeTool
from apps.agent.tools.notification import NotifyUserTool
from apps.agent.tools.registry import ToolRegistry
from apps.agent.tools.telephony import EndCallTool, TransferCallTool


@pytest.mark.asyncio
async def test_get_contact_tool() -> None:
    """Verify GetContactTool retrieves contacts by name, phone, or relationship."""
    tool = GetContactTool()

    # Search by name
    res_name = await tool.execute(query="Sneha")
    assert res_name.success is True
    assert res_name.data["found"] is True
    assert res_name.data["contacts"][0]["name"] == "Sneha"
    assert res_name.data["contacts"][0]["relationship"] == "colleague"

    # Search by phone
    res_phone = await tool.execute(query="+91-9811122233")
    assert res_phone.success is True
    assert res_phone.data["found"] is True
    assert res_phone.data["contacts"][0]["name"] == "Mummy"

    # Search not found
    res_none = await tool.execute(query="NonExistentContact123")
    assert res_none.success is True
    assert res_none.data["found"] is False


@pytest.mark.asyncio
async def test_get_caller_history_tool() -> None:
    """Verify GetCallerHistoryTool retrieves past interaction history."""
    tool = GetCallerHistoryTool()

    # Known caller history
    res = await tool.execute(caller_id="+91-9811122233")
    assert res.success is True
    assert res.data["total_past_calls"] >= 2
    assert "Mummy" in res.data["history"][0]["summary"]

    # Unknown caller history
    res_unknown = await tool.execute(caller_id="+91-9999999999")
    assert res_unknown.success is True
    assert res_unknown.data["total_past_calls"] == 0


@pytest.mark.asyncio
async def test_save_caller_message_tool() -> None:
    """Verify SaveCallerMessageTool validates and records messages."""
    tool = SaveCallerMessageTool()

    res = await tool.execute(
        caller_name="Priya",
        message="Please call back regarding Google HR interview schedule.",
        phone_number="+91-9988776652",
        urgency="high",
        category="recruiter",
    )
    assert res.success is True
    assert res.data["status"] == "saved"
    assert res.data["caller_name"] == "Priya"
    assert res.data["urgency"] == "high"


@pytest.mark.asyncio
async def test_search_knowledge_tool() -> None:
    """Verify SearchKnowledgeTool queries owner's allowlisted availability and facts."""
    tool = SearchKnowledgeTool()

    # Calendar query
    res = await tool.execute(query="meeting availability")
    assert res.success is True
    assert res.data["found_count"] >= 1
    assert "2 PM and 6 PM" in res.data["results"][0]["content"]

    # Project query
    res_proj = await tool.execute(query="voice agent", category="project")
    assert res_proj.success is True
    assert res_proj.data["found_count"] >= 1


@pytest.mark.asyncio
async def test_notify_user_tool() -> None:
    """Verify NotifyUserTool delivers notification records."""
    tool = NotifyUserTool()

    res = await tool.execute(
        title="Urgent HR Call",
        message="Priya from Google HR called regarding AI Engineer interview.",
        urgency="high",
        channel="telegram",
    )
    assert res.success is True
    assert res.data["delivered"] is True
    assert res.data["channel"] == "telegram"
    assert len(tool.sent_notifications) == 1


@pytest.mark.asyncio
async def test_transfer_call_tool() -> None:
    """Verify TransferCallTool initiates call transfer."""
    tool = TransferCallTool()

    res = await tool.execute(
        target="owner",
        reason="Google recruiter interview discussion",
        urgency="high",
    )
    assert res.success is True
    assert res.data["transfer_initiated"] is True
    assert res.data["target"] == "owner"
    assert len(tool.transfer_events) == 1


@pytest.mark.asyncio
async def test_end_call_tool() -> None:
    """Verify EndCallTool concludes call with reason."""
    tool = EndCallTool()

    res = await tool.execute(
        reason="normal_completion",
        polite_closing_note="Thank you, goodbye!",
    )
    assert res.success is True
    assert res.data["call_ended"] is True
    assert len(tool.termination_events) == 1


@pytest.mark.asyncio
async def test_tool_registry_validation_and_audit() -> None:
    """Verify ToolRegistry validates inputs, blocks denied tools, and records audit trails."""
    registry = ToolRegistry()

    # 1. Valid execution with audit trail
    res_time = await registry.execute("get_current_time", {})
    assert res_time.success is True
    assert len(registry.audit_log) >= 1
    last_audit = registry.audit_log[-1]
    assert last_audit.tool_name == "get_current_time"
    assert last_audit.success is True

    # 2. Invalid arguments validation error
    res_inv = await registry.execute("get_contact", {})  # Missing required 'query'
    assert res_inv.success is False
    assert "Invalid arguments" in (res_inv.error or "")

    # 3. Hallucinated / unknown tool call
    res_fake = await registry.execute("non_existent_fake_tool_xyz", {"foo": "bar"})
    assert res_fake.success is False
    assert "is not recognized" in (res_fake.error or "")

    # 4. Denied permission tool
    time_tool = registry.get("get_current_time")
    assert time_tool is not None
    original_perm = time_tool.permission_level
    try:
        time_tool.permission_level = PermissionLevel.DENIED
        res_denied = await registry.execute("get_current_time", {})
        assert res_denied.success is False
        assert "permission is denied" in (res_denied.error or "")
    finally:
        time_tool.permission_level = original_perm
