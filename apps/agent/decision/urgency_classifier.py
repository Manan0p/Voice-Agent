import re

from apps.agent.decision.models import IntentCategory, UrgencyAssessment, UrgencyLevel


class UrgencyClassifier:
    """Evaluates the urgency and time-sensitivity of the incoming call."""

    CRITICAL_PATTERNS = re.compile(
        r"\b(emergency|hospital|accident|police|production down|server crash|p0 bug|critical outage|arrest warrant|court summons|customs department)\b",
        re.I,
    )

    HIGH_PATTERNS = re.compile(
        r"\b(interview|job offer|urgent|urgently|at the gate|standing outside|doorbell|as soon as possible|immediate|turant|jaldi|p1 bug|bug in production)\b",
        re.I,
    )
    MEDIUM_PATTERNS = re.compile(
        r"\b(kal morning|tomorrow|reschedule|due date|technician|bill payment|schedule|meeting time)\b",
        re.I,
    )

    def evaluate(
        self, utterance: str, intent_category: IntentCategory = IntentCategory.UNKNOWN
    ) -> UrgencyAssessment:
        """Evaluate urgency level and compute priority score."""
        clean_text = utterance.strip()
        if not clean_text:
            return UrgencyAssessment(
                level=UrgencyLevel.LOW, score=0.1, time_sensitive=False, reason="Empty utterance"
            )

        # 1. Critical tier
        if (
            self.CRITICAL_PATTERNS.search(clean_text)
            or intent_category == IntentCategory.URGENT_PERSONAL
        ):
            return UrgencyAssessment(
                level=UrgencyLevel.CRITICAL,
                score=0.95,
                time_sensitive=True,
                reason="Immediate emergency or critical issue detected",
            )

        # 2. High tier
        if self.HIGH_PATTERNS.search(clean_text) or intent_category in {
            IntentCategory.JOB_INTERVIEW,
            IntentCategory.DELIVERY,
        }:
            return UrgencyAssessment(
                level=UrgencyLevel.HIGH,
                score=0.80,
                time_sensitive=True,
                reason="High priority interview or live delivery partner interaction",
            )

        # 3. Medium tier
        if self.MEDIUM_PATTERNS.search(clean_text) or intent_category in {
            IntentCategory.WORK_COLLABORATION,
            IntentCategory.UTILITY_MAINTENANCE,
        }:
            return UrgencyAssessment(
                level=UrgencyLevel.MEDIUM,
                score=0.50,
                time_sensitive=False,
                reason="Standard action item or schedule coordination",
            )

        # 4. Low tier
        return UrgencyAssessment(
            level=UrgencyLevel.LOW,
            score=0.20,
            time_sensitive=False,
            reason="Routine casual inquiry or informational call",
        )
