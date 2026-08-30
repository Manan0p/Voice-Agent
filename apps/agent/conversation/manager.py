from typing import Any

from apps.agent.llm.base import LLMMessage, Role, ToolCall
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.conversation.manager")


class ConversationManager:
    """Manages multi-turn conversation state, history, and context window limits."""

    def __init__(self, max_turns: int = 30) -> None:
        self.max_turns = max_turns
        self.messages: list[LLMMessage] = []
        self._turn_count: int = 0

    @property
    def turn_count(self) -> int:
        """Return total number of user-assistant interaction turns."""
        return self._turn_count

    def add_user_message(self, content: str) -> LLMMessage:
        """Append a user message and increment turn count."""
        msg = LLMMessage(role=Role.USER, content=content)
        self.messages.append(msg)
        self._turn_count += 1
        self._trim_history()
        return msg

    def add_assistant_message(
        self,
        content: str,
        tool_calls: list[ToolCall] | None = None,
    ) -> LLMMessage:
        """Append an assistant response."""
        msg = LLMMessage(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls or [],
        )
        self.messages.append(msg)
        self._trim_history()
        return msg

    def add_tool_message(
        self,
        name: str,
        content: str,
        tool_call_id: str | None = None,
    ) -> LLMMessage:
        """Append tool execution output."""
        msg = LLMMessage(
            role=Role.TOOL,
            name=name,
            content=content,
            tool_call_id=tool_call_id,
        )
        self.messages.append(msg)
        return msg

    def get_messages(self) -> list[LLMMessage]:
        """Return the current active message list."""
        return list(self.messages)

    def _trim_history(self) -> None:
        """Ensure message count stays within the sliding window."""
        # Each turn is typically ~2 messages (user + assistant)
        max_messages = self.max_turns * 2
        if len(self.messages) > max_messages:
            # Keep most recent messages
            excess = len(self.messages) - max_messages
            self.messages = self.messages[excess:]
            logger.debug("Trimmed %d older messages from conversation history.", excess)

    def clear(self) -> None:
        """Reset conversation state."""
        self.messages.clear()
        self._turn_count = 0

    def to_transcript(self) -> list[dict[str, Any]]:
        """Export conversation messages to a raw transcript format."""
        transcript = []
        for msg in self.messages:
            transcript.append(
                {
                    "role": str(msg.role),
                    "content": msg.content,
                    "name": msg.name,
                    "tool_calls": [
                        {"name": tc.name, "arguments": tc.arguments} for tc in msg.tool_calls
                    ]
                    if msg.tool_calls
                    else None,
                }
            )
        return transcript
