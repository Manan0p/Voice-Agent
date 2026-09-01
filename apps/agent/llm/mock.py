from collections.abc import AsyncGenerator
from typing import Any

from apps.agent.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolCall


class MockLLMProvider(LLMProvider):
    """Deterministic Mock LLM Provider for unit testing and offline evals."""

    def __init__(
        self,
        default_response: str = "Hello! I am Manan's AI assistant. How can I help you today?",
        custom_responses: dict[str, str] | None = None,
        tool_call_triggers: dict[str, ToolCall] | None = None,
    ) -> None:
        self.default_response = default_response
        self.custom_responses = custom_responses or {}
        self.tool_call_triggers = tool_call_triggers or {}
        self.call_history: list[list[LLMMessage]] = []

    async def generate(
        self,
        messages: list[LLMMessage],
        system_instruction: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> LLMResponse:
        """Return predefined or matched response."""
        self.call_history.append(messages)
        if not messages:
            return LLMResponse(content=self.default_response, latency_ms=5.0)

        last_msg = messages[-1]
        last_content = last_msg.content or ""

        # Check for tool call trigger only if last message was from user
        if last_msg.role == "user":
            for trigger_key, tool_call in self.tool_call_triggers.items():
                if trigger_key.lower() in last_content.lower():
                    return LLMResponse(
                        content="",
                        tool_calls=[tool_call],
                        finish_reason="tool_calls",
                        latency_ms=15.0,
                        prompt_tokens=20,
                        completion_tokens=10,
                    )

        # Check for matching custom response
        for key, resp in self.custom_responses.items():
            if key.lower() in last_content.lower():
                return LLMResponse(
                    content=resp,
                    latency_ms=10.0,
                    prompt_tokens=25,
                    completion_tokens=15,
                )

        return LLMResponse(
            content=self.default_response,
            latency_ms=5.0,
            prompt_tokens=10,
            completion_tokens=10,
        )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> AsyncGenerator[str, None]:
        """Stream words one by one."""
        self.call_history.append(messages)
        last_content = messages[-1].content if messages else ""
        text = self.custom_responses.get(last_content, self.default_response)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
