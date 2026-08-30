from dataclasses import dataclass, field
from typing import Any

from apps.agent.prompts.system import build_system_prompt


@dataclass
class CallerContext:
    """Metadata regarding the caller and current active session."""

    caller_id: str = "unknown"
    caller_name: str | None = None
    relationship: str | None = None
    language_hint: str | None = None
    extra_notes: list[str] = field(default_factory=list)


class ContextManager:
    """Assembles and manages dynamic runtime context for the agent."""

    def __init__(self, owner_name: str = "Manan") -> None:
        self.owner_name = owner_name
        self.caller_context = CallerContext()
        self.session_metadata: dict[str, Any] = {}

    def set_caller(
        self,
        caller_id: str,
        caller_name: str | None = None,
        relationship: str | None = None,
        language_hint: str | None = None,
    ) -> None:
        """Update caller identity and context."""
        self.caller_context.caller_id = caller_id
        self.caller_context.caller_name = caller_name
        self.caller_context.relationship = relationship
        self.caller_context.language_hint = language_hint

    def add_note(self, note: str) -> None:
        """Add context note during the call."""
        self.caller_context.extra_notes.append(note)

    def get_system_instruction(self) -> str:
        """Render complete system instruction string with contextual variables."""
        additional_notes = (
            "; ".join(self.caller_context.extra_notes) if self.caller_context.extra_notes else None
        )
        return build_system_prompt(
            owner_name=self.owner_name,
            caller_name=self.caller_context.caller_name,
            caller_relationship=self.caller_context.relationship,
            additional_context=additional_notes,
        )
