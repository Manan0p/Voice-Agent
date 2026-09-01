from apps.agent.decision.caller_resolver import CallerResolver
from apps.agent.decision.intent_classifier import IntentClassifier
from apps.agent.decision.models import (
    AgentAction,
    CallerRelationship,
    DecisionState,
    IntentCategory,
    RiskLevel,
    UrgencyLevel,
)
from apps.agent.decision.risk_classifier import RiskClassifier
from apps.agent.decision.urgency_classifier import UrgencyClassifier
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.decision.engine")


class DecisionEngine:
    """Core decision & state triage orchestrator combining identity, intent, urgency, and risk."""

    def __init__(
        self,
        caller_resolver: CallerResolver | None = None,
        intent_classifier: IntentClassifier | None = None,
        urgency_classifier: UrgencyClassifier | None = None,
        risk_classifier: RiskClassifier | None = None,
    ) -> None:
        self.caller_resolver = caller_resolver or CallerResolver()
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.urgency_classifier = urgency_classifier or UrgencyClassifier()
        self.risk_classifier = risk_classifier or RiskClassifier()

    def evaluate(
        self,
        caller_id: str,
        utterance: str,
        initial_name: str | None = None,
    ) -> DecisionState:
        """Evaluate incoming turn and synthesize full decision state."""
        caller = self.caller_resolver.resolve(
            caller_id=caller_id, initial_name=initial_name, utterance=utterance
        )
        intent = self.intent_classifier.classify(utterance)
        urgency = self.urgency_classifier.evaluate(utterance, intent_category=intent.category)
        risk = self.risk_classifier.evaluate(utterance)

        action = AgentAction.HANDLE_AUTONOMOUSLY
        rationale = ""
        requires_human = False
        should_terminate = False

        # 1. High Risk & Scam Security Triage
        if risk.level == RiskLevel.HIGH_RISK_SCAM:
            action = AgentAction.BLOCK_AND_TERMINATE
            rationale = "High-risk scam or coercive extortion threat detected. Immediate termination required."
            should_terminate = True

        elif risk.level == RiskLevel.CREDENTIAL_FISHING:
            # Deliveries asking for OTP is expected; random callers asking for bank OTP is blocked
            if (
                caller.relationship == CallerRelationship.DELIVERY
                or intent.category == IntentCategory.DELIVERY
            ):
                action = AgentAction.HANDLE_AUTONOMOUSLY
                rationale = "Delivery partner requested verification OTP. Handled through secure verification rules."
            else:
                action = AgentAction.HANDLE_AUTONOMOUSLY
                rationale = "Sensitive authentication credentials requested. Refuse to share confidential information."

        # 2. Critical & Emergency Triage
        elif (
            urgency.level == UrgencyLevel.CRITICAL
            or intent.category == IntentCategory.URGENT_PERSONAL
        ):
            action = AgentAction.INTERRUPT_USER
            rationale = "Critical emergency or urgent personal situation detected. Immediately interrupt user."
            requires_human = True

        # 3. High-Priority Job Interviews & Critical Work Outages
        elif intent.category == IntentCategory.JOB_INTERVIEW or (
            intent.category == IntentCategory.WORK_COLLABORATION
            and urgency.level == UrgencyLevel.HIGH
        ):
            action = AgentAction.INTERRUPT_USER
            rationale = (
                f"High priority {intent.category.value} detected. Notify and interrupt user."
            )
            requires_human = True

        # 4. Logistics and Deliveries
        elif (
            intent.category == IntentCategory.DELIVERY
            or caller.relationship == CallerRelationship.DELIVERY
        ):
            action = AgentAction.HANDLE_AUTONOMOUSLY
            rationale = "Standard delivery coordination handled autonomously by AI assistant."

        # 5. Marketing & Spam
        elif (
            intent.category == IntentCategory.SALES_MARKETING
            or caller.relationship == CallerRelationship.SPAM
        ):
            action = AgentAction.HANDLE_AUTONOMOUSLY
            rationale = "Sales/marketing call. Politely decline on user's behalf."

        # 6. Routine Tasks & Messaging
        elif intent.category in {
            IntentCategory.WORK_COLLABORATION,
            IntentCategory.UTILITY_MAINTENANCE,
        }:
            action = AgentAction.TAKE_MESSAGE
            rationale = (
                "Non-urgent operational task or maintenance coordination. Note details for user."
            )

        else:
            action = AgentAction.HANDLE_AUTONOMOUSLY
            rationale = "Standard conversational turn handled autonomously."

        decision = DecisionState(
            caller=caller,
            intent=intent,
            urgency=urgency,
            risk=risk,
            recommended_action=action,
            action_rationale=rationale,
            requires_human_intervention=requires_human,
            should_terminate_call=should_terminate,
        )

        logger.info(
            "Decision computed: Action=%s, Intent=%s, Urgency=%s, Risk=%s",
            action.value,
            intent.category.value,
            urgency.level.value,
            risk.level.value,
        )

        return decision
