import pytest

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.llm.mock import MockLLMProvider
from apps.agent.tools.builtin import GetCurrentTimeTool, SaveCallerMessageTool
from apps.agent.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_multi_turn_conversation_retention() -> None:
    """Simulate a realistic 12-turn text call verifying context and memory retention."""
    script_responses = {
        "hello": "Hello! I am Manan's AI call assistant. Who is calling, please?",
        "rahul here": "Hi Rahul! How can I help you today?",
        "bhai project update": "Haan Rahul bhai, Manan is currently unavailable, but I can take notes on the project update.",
        "deployment is done": "Noted that deployment is done. Anything specific regarding the release date?",
        "release is on wednesday": "Got it, Wednesday release. I will inform Manan.",
        "what time is it right now?": "Let me check the time for you.",
        "thanks": "You're welcome! Shall I leave a summary message for Manan?",
        "yes please": "I have recorded the full message for Manan. Have a great day!",
        "bye": "Goodbye Rahul, take care!",
    }

    mock_llm = MockLLMProvider(
        default_response="Understood, I have noted that down.",
        custom_responses=script_responses,
    )

    context = ContextManager(owner_name="Manan")
    context.set_caller(caller_id="+91-9876543210", caller_name="Rahul")

    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    registry.register(SaveCallerMessageTool())

    engine = AgentEngine(
        llm_provider=mock_llm,
        context_manager=context,
        tool_registry=registry,
    )

    user_turns = [
        "Hello",
        "Rahul here, his colleague from work.",
        "Bhai project update dena tha.",
        "The deployment is done on staging server.",
        "Our release is on Wednesday.",
        "What time is it right now?",
        "Thanks for the help.",
        "Yes please, tell him to call me if needed.",
        "Bye!",
    ]

    for turn_idx, turn_text in enumerate(user_turns, start=1):
        result = await engine.step(turn_text)
        assert result.turn_index == turn_idx
        assert len(result.response_text) > 0
        assert result.total_latency_ms >= 0.0

    # Verify conversation history size and state
    messages = engine.conversation.get_messages()
    assert len(messages) == len(user_turns) * 2  # 9 user + 9 assistant
    assert engine.conversation.turn_count == len(user_turns)

    # Check transcript export completeness
    transcript = engine.conversation.to_transcript()
    assert len(transcript) == len(user_turns) * 2
    assert transcript[0]["content"] == "Hello"
    assert transcript[-1]["role"] == "assistant"
