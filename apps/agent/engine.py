import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from apps.agent.context.manager import ContextManager
from apps.agent.conversation.manager import ConversationManager
from apps.agent.llm.base import LLMProvider, ToolCall
from apps.agent.llm.factory import get_llm_provider
from apps.agent.tools.builtin import GetCurrentTimeTool, SaveCallerMessageTool
from apps.agent.tools.registry import ToolRegistry
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.engine")


@dataclass
class AgentTurnResult:
    """Detailed result container for a single conversational turn."""

    response_text: str
    turn_index: int
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    total_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0


class AgentEngine:
    """High-level Orchestrator managing conversation lifecycle, context, LLM, and tools."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        context_manager: ContextManager | None = None,
        conversation_manager: ConversationManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.llm = llm_provider or get_llm_provider()
        self.context = context_manager or ContextManager()
        self.conversation = conversation_manager or ConversationManager()
        self.tools = tool_registry or ToolRegistry()

        # Register default builtin tools if empty
        if not self.tools.list_tools():
            self.tools.register(GetCurrentTimeTool())
            self.tools.register(SaveCallerMessageTool())

    async def step(self, user_input: str) -> AgentTurnResult:
        """Process a single turn of user input and return the assistant response."""
        start_time = time.perf_counter()

        # 1. Append user message to history
        self.conversation.add_user_message(user_input)

        system_instruction = self.context.get_system_instruction()
        tool_schemas = self.tools.get_schemas()
        caller_id = self.context.caller_context.caller_id

        executed_tool_calls: list[ToolCall] = []
        executed_tool_results: list[dict[str, Any]] = []
        total_llm_latency = 0.0

        # Max tool call execution depth per turn to prevent infinite loops
        max_tool_iterations = 3
        iteration = 0

        while iteration < max_tool_iterations:
            iteration += 1
            messages = self.conversation.get_messages()

            try:
                response = await self.llm.generate(
                    messages=messages,
                    system_instruction=system_instruction,
                    tools=tool_schemas if tool_schemas else None,
                )
            except Exception as e:
                logger.error("LLM generation failed: %s", str(e))
                # Fallback message
                fallback = "I apologize, but I am having temporary difficulty connecting. Could you please repeat that?"
                self.conversation.add_assistant_message(fallback)
                return AgentTurnResult(
                    response_text=fallback,
                    turn_index=self.conversation.turn_count,
                    total_latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            total_llm_latency += response.latency_ms

            # Check if model requested tool execution
            if response.tool_calls:
                for tc in response.tool_calls:
                    executed_tool_calls.append(tc)
                    # Add assistant tool-call message
                    self.conversation.add_assistant_message(
                        content=response.content,
                        tool_calls=[tc],
                    )

                    # Execute tool
                    tool_res = await self.tools.execute(
                        name=tc.name,
                        arguments=tc.arguments,
                        caller_id=caller_id,
                    )
                    executed_tool_results.append(
                        {
                            "tool": tc.name,
                            "success": tool_res.success,
                            "data": tool_res.data,
                            "error": tool_res.error,
                        }
                    )

                    # Add tool response message
                    content_str = (
                        str(tool_res.data) if tool_res.success else f"Error: {tool_res.error}"
                    )
                    self.conversation.add_tool_message(
                        name=tc.name,
                        content=content_str,
                        tool_call_id=tc.id,
                    )
                # Loop back to generate response incorporating tool output
                continue

            # Model produced a final textual response
            self.conversation.add_assistant_message(response.content)
            total_latency = (time.perf_counter() - start_time) * 1000.0

            return AgentTurnResult(
                response_text=response.content,
                turn_index=self.conversation.turn_count,
                tool_calls=executed_tool_calls,
                tool_results=executed_tool_results,
                total_latency_ms=total_latency,
                llm_latency_ms=total_llm_latency,
            )

        # Fallback if tool iterations exceeded
        final_fallback = "I noted down that information for Manan."
        self.conversation.add_assistant_message(final_fallback)
        return AgentTurnResult(
            response_text=final_fallback,
            turn_index=self.conversation.turn_count,
            tool_calls=executed_tool_calls,
            tool_results=executed_tool_results,
            total_latency_ms=(time.perf_counter() - start_time) * 1000.0,
            llm_latency_ms=total_llm_latency,
        )

    async def step_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream conversational response for real-time text/voice output."""
        self.conversation.add_user_message(user_input)
        system_instruction = self.context.get_system_instruction()
        messages = self.conversation.get_messages()

        full_content = ""
        async for chunk in self.llm.generate_stream(
            messages=messages,
            system_instruction=system_instruction,
        ):
            full_content += chunk
            yield chunk

        self.conversation.add_assistant_message(full_content)
