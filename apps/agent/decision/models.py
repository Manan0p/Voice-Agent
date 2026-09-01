from enum import StrEnum

from pydantic import BaseModel, Field


class CallerRelationship(StrEnum):
    """Relationship of the caller to the user."""

    SELF = "self"
    FAMILY = "family"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    RECRUITER = "recruiter"
    DELIVERY = "delivery"
    BUSINESS = "business"
    UNKNOWN = "unknown"
    SPAM = "spam"


class IntentCategory(StrEnum):
    """Categorized purpose or intent of the call."""

    JOB_INTERVIEW = "job_interview"
    DELIVERY = "delivery"
    URGENT_PERSONAL = "urgent_personal"
    WORK_COLLABORATION = "work_collaboration"
    UTILITY_MAINTENANCE = "utility_maintenance"
    GENERAL_INQUIRY = "general_inquiry"
    SALES_MARKETING = "sales_marketing"
    SPAM_SCAM = "spam_scam"
    UNKNOWN = "unknown"


class UrgencyLevel(StrEnum):
    """Urgency rating of the call."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(StrEnum):
    """Security and safety risk rating of the call."""

    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    HIGH_RISK_SCAM = "high_risk_scam"
    CREDENTIAL_FISHING = "credential_fishing"


class AgentAction(StrEnum):
    """Optimal action decided by the decision engine for the call turn."""

    HANDLE_AUTONOMOUSLY = "handle_autonomously"
    TAKE_MESSAGE = "take_message"
    INTERRUPT_USER = "interrupt_user"
    TRANSFER_TO_USER = "transfer_to_user"
    BLOCK_AND_TERMINATE = "block_and_terminate"
    ASK_CLARIFICATION = "ask_clarification"


class CallerIdentity(BaseModel):
    """Resolved identity and trust status of the caller."""

    caller_id: str = "+91-0000000000"
    caller_name: str | None = None
    relationship: CallerRelationship = CallerRelationship.UNKNOWN
    organization: str | None = None
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    is_known_contact: bool = False


class CallIntent(BaseModel):
    """Extracted intent assessment of the call."""

    category: IntentCategory = IntentCategory.UNKNOWN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    summary: str = "General call"
    key_entities: list[str] = Field(default_factory=list)


class UrgencyAssessment(BaseModel):
    """Urgency assessment details."""

    level: UrgencyLevel = UrgencyLevel.LOW
    score: float = Field(default=0.2, ge=0.0, le=1.0)
    time_sensitive: bool = False
    reason: str = "Standard non-urgent inquiry"


class RiskAssessment(BaseModel):
    """Security and fraud assessment details."""

    level: RiskLevel = RiskLevel.SAFE
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    requested_sensitive_info: bool = False
    flags: list[str] = Field(default_factory=list)
    reason: str = "No security risks detected"


class DecisionState(BaseModel):
    """Complete aggregated decision state produced by the DecisionEngine."""

    caller: CallerIdentity
    intent: CallIntent
    urgency: UrgencyAssessment
    risk: RiskAssessment
    recommended_action: AgentAction
    action_rationale: str
    requires_human_intervention: bool = False
    should_terminate_call: bool = False
