import pytest

from apps.agent.engine import AgentEngine
from apps.agent.llm.base import LLMResponse, ToolCall
from apps.agent.llm.mock import MockLLMProvider
from apps.agent.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_agent_engine_multi_tool_execution_flow() -> None:
    """Verify AgentEngine executes tool calls, records outputs in messages, and completes turn."""
    # Sequence of responses: step 1 emits 2 tool calls, step 2 provides final answer
    step1_response = LLMResponse(
        content="",
        tool_calls=[
            ToolCall(
                id="call_contact_1",
                name="get_contact",
                arguments={"query": "Sneha"},
            ),
            ToolCall(
                id="call_kb_1",
                name="search_knowledge",
                arguments={"query": "meeting availability"},
            ),
        ],
    )
    step2_response = LLMResponse(
        content="Sneha is listed as a colleague, and Manan is available for meetings between 2 PM and 6 PM.",
        tool_calls=None,
    )

    class MultiStepMockLLM(MockLLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.responses = [step1_response, step2_response]
            self.call_idx = 0

        async def generate(self, messages, system_instruction=None, tools=None):
            if self.call_idx < len(self.responses):
                res = self.responses[self.call_idx]
                self.call_idx += 1
                return res
            return step2_response

    custom_llm = MultiStepMockLLM()
    registry = ToolRegistry()
    engine = AgentEngine(llm_provider=custom_llm, tool_registry=registry)

    result = await engine.step("Can you check if Sneha is a contact and when Manan is free?")

    assert (
        result.response_text
        == "Sneha is listed as a colleague, and Manan is available for meetings between 2 PM and 6 PM."
    )
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].name == "get_contact"
    assert result.tool_calls[1].name == "search_knowledge"
    assert len(result.tool_results) == 2
    assert result.tool_results[0]["success"] is True
    assert result.tool_results[1]["success"] is True

    # Verify audit log in registry
    assert len(registry.audit_log) == 2
    assert registry.audit_log[0].tool_name == "get_contact"
    assert registry.audit_log[1].tool_name == "search_knowledge"


@pytest.mark.asyncio
async def test_agent_engine_hallucinated_tool_recovery() -> None:
    """Verify AgentEngine handles hallucinated/invalid tool call gracefully and recovers."""
    hallucinated_call = LLMResponse(
        content="",
        tool_calls=[
            ToolCall(
                id="call_hallucinated_1",
                name="unregistered_crypto_trade_tool",
                arguments={"amount": 1000},
            )
        ],
    )
    recovery_response = LLMResponse(
        content="I cannot perform that action, but I can note a message for Manan.",
        tool_calls=None,
    )

    class HallucinatingMockLLM(MockLLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.call_idx = 0

        async def generate(self, messages, system_instruction=None, tools=None):
            if self.call_idx == 0:
                self.call_idx += 1
                return hallucinated_call
            return recovery_response

    mock_llm = HallucinatingMockLLM()
    registry = ToolRegistry()
    engine = AgentEngine(llm_provider=mock_llm, tool_registry=registry)

    result = await engine.step("Execute trade 1000.")

    assert (
        result.response_text == "I cannot perform that action, but I can note a message for Manan."
    )
    assert len(result.tool_calls) == 1
    assert result.tool_results[0]["success"] is False
    assert "is not recognized" in (result.tool_results[0]["error"] or "")
