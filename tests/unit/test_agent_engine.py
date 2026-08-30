import pytest

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.llm.base import ToolCall
from apps.agent.llm.mock import MockLLMProvider
from apps.agent.tools.builtin import SaveCallerMessageTool
from apps.agent.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_agent_engine_basic_step() -> None:
    """Verify single turn step through AgentEngine."""
    mock_llm = MockLLMProvider(
        custom_responses={
            "hello": "Namaste! Main Manan ka AI assistant hoon. Kaise madad kar sakta hoon?"
        }
    )
    context = ContextManager(owner_name="Manan")
    context.set_caller(caller_id="+91-9999999999", caller_name="Amit")

    engine = AgentEngine(
        llm_provider=mock_llm,
        context_manager=context,
    )

    result = await engine.step("Hello")
    assert result.turn_index == 1
    assert "Manan ka AI assistant" in result.response_text
    assert result.total_latency_ms >= 0.0


@pytest.mark.asyncio
async def test_agent_engine_tool_execution_flow() -> None:
    """Verify tool call trigger, execution, and subsequent response generation."""
    tool_call = ToolCall(
        id="call_1",
        name="save_caller_message",
        arguments={
            "caller_name": "Rohan",
            "message_content": "Interview is confirmed for tomorrow 10 AM.",
        },
    )

    mock_llm = MockLLMProvider(
        default_response="Message has been saved for Manan.",
        tool_call_triggers={"confirm": tool_call},
    )

    registry = ToolRegistry()
    registry.register(SaveCallerMessageTool())

    engine = AgentEngine(
        llm_provider=mock_llm,
        tool_registry=registry,
    )

    result = await engine.step("Please confirm the interview with Manan.")
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "save_caller_message"
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["success"] is True


@pytest.mark.asyncio
async def test_agent_engine_streaming() -> None:
    """Verify stream generation across multiple chunks."""
    mock_llm = MockLLMProvider(custom_responses={"hi": "Hello this is a streamed voice response."})
    engine = AgentEngine(llm_provider=mock_llm)

    chunks = []
    async for chunk in engine.step_stream("hi"):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "streamed voice response" in full_text
    assert len(engine.conversation.get_messages()) == 2
