from dataclasses import dataclass, field
from typing import Any

from apps.agent.decision.engine import DecisionEngine
from apps.agent.decision.models import DecisionState
from apps.agent.language.policy import LanguagePolicy, LanguagePolicyDecision, LanguagePolicyMode
from apps.agent.language.tracker import ConversationalLanguageState, LanguageTracker
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
    """Assembles and manages dynamic runtime context, linguistic policy, and state decisions for the agent."""

    def __init__(
        self,
        owner_name: str = "Manan",
        policy_mode: LanguagePolicyMode = LanguagePolicyMode.MIRROR,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        self.owner_name = owner_name
        self.caller_context = CallerContext()
        self.session_metadata: dict[str, Any] = {}
        self.language_tracker = LanguageTracker()
        self.language_policy = LanguagePolicy(mode=policy_mode)
        self.decision_engine = decision_engine or DecisionEngine()
        self.latest_language_decision: LanguagePolicyDecision | None = None
        self.latest_language_state: ConversationalLanguageState | None = None
        self.latest_decision_state: DecisionState | None = None

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

    def update_state(self, user_utterance: str) -> DecisionState:
        """Process incoming user utterance, update language momentum and compute decision state."""
        # 1. Update language
        self.latest_language_state = self.language_tracker.update(user_utterance)
        self.latest_language_decision = self.language_policy.decide(self.latest_language_state)

        # 2. Compute decision triage state
        self.latest_decision_state = self.decision_engine.evaluate(
            caller_id=self.caller_context.caller_id,
            utterance=user_utterance,
            initial_name=self.caller_context.caller_name,
        )

        # 3. Synchronize resolved caller info back to context if newly detected
        if self.latest_decision_state.caller.caller_name and not self.caller_context.caller_name:
            self.caller_context.caller_name = self.latest_decision_state.caller.caller_name

        if (
            self.latest_decision_state.caller.relationship != "unknown"
            and not self.caller_context.relationship
        ):
            self.caller_context.relationship = self.latest_decision_state.caller.relationship.value

        return self.latest_decision_state

    def update_language(self, user_utterance: str) -> LanguagePolicyDecision:
        """Process incoming user utterance and update language policy."""
        self.latest_language_state = self.language_tracker.update(user_utterance)
        self.latest_language_decision = self.language_policy.decide(self.latest_language_state)
        return self.latest_language_decision

    def get_system_instruction(self) -> str:
        """Render complete system instruction string with contextual variables, language policy, and decision state."""
        additional_notes = (
            "; ".join(self.caller_context.extra_notes) if self.caller_context.extra_notes else None
        )
        language_prompt = (
            self.latest_language_decision.instruction_prompt
            if self.latest_language_decision
            else None
        )

        return build_system_prompt(
            owner_name=self.owner_name,
            caller_name=self.caller_context.caller_name,
            caller_relationship=self.caller_context.relationship,
            additional_context=additional_notes,
            language_instruction=language_prompt,
        )
