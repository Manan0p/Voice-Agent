from apps.agent.decision.caller_resolver import CallerResolver
from apps.agent.decision.engine import DecisionEngine
from apps.agent.decision.intent_classifier import IntentClassifier
from apps.agent.decision.models import (
    AgentAction,
    CallerRelationship,
    IntentCategory,
    RiskLevel,
    UrgencyLevel,
)
from apps.agent.decision.risk_classifier import RiskClassifier
from apps.agent.decision.urgency_classifier import UrgencyClassifier


def test_caller_resolver_known_contact() -> None:
    """Verify known contact resolution by phone number."""
    resolver = CallerResolver()
    res = resolver.resolve(caller_id="+91-9811122233")
    assert res.caller_name == "Mummy"
    assert res.relationship == CallerRelationship.FAMILY
    assert res.trust_score == 1.0
    assert res.is_known_contact is True


def test_caller_resolver_speech_extraction() -> None:
    """Verify relationship and organization extraction from speech."""
    resolver = CallerResolver()
    res = resolver.resolve(
        caller_id="+91-9999999999",
        utterance="Hi, this is Priya from Google HR calling regarding an interview.",
    )
    assert res.caller_name == "Priya"
    assert res.relationship == CallerRelationship.RECRUITER
    assert res.organization == "Google"
    assert res.is_known_contact is True


def test_intent_classifier_scenarios() -> None:
    """Verify intent categorization for diverse call types."""
    classifier = IntentClassifier()

    # Job interview
    intent_job = classifier.classify("Calling regarding your technical interview round 2 tomorrow.")
    assert intent_job.category == IntentCategory.JOB_INTERVIEW

    # Delivery
    intent_del = classifier.classify("Bhaiya Zomato delivery boy hoon, gate pe khada hoon.")
    assert intent_del.category == IntentCategory.DELIVERY

    # Emergency
    intent_emg = classifier.classify("Emergency hospital accident near home.")
    assert intent_emg.category == IntentCategory.URGENT_PERSONAL

    # Scam
    intent_scam = classifier.classify("Your bank account is suspended due to KYC blocked.")
    assert intent_scam.category == IntentCategory.SPAM_SCAM


def test_urgency_classifier_levels() -> None:
    """Verify urgency scoring thresholds."""
    classifier = UrgencyClassifier()

    crit = classifier.evaluate("Emergency, doctor calling from hospital immediately!")
    assert crit.level == UrgencyLevel.CRITICAL
    assert crit.time_sensitive is True

    high = classifier.evaluate("Hiring manager is waiting on zoom for interview right now.")
    assert high.level == UrgencyLevel.HIGH

    med = classifier.evaluate("Water supply maintenance notice for tomorrow morning.")
    assert med.level == UrgencyLevel.MEDIUM


def test_risk_classifier_detection() -> None:
    """Verify risk assessment flags OTP requests and scam threats."""
    classifier = RiskClassifier()

    # OTP Request
    risk_otp = classifier.evaluate(
        "Please share the 6-digit OTP verification code received on SMS."
    )
    assert risk_otp.level == RiskLevel.CREDENTIAL_FISHING
    assert risk_otp.requested_sensitive_info is True
    assert "credential_request" in risk_otp.flags

    # Police extortion threat
    risk_threat = classifier.evaluate(
        "Customs department police arrest warrant issued on your Aadhaar card."
    )
    assert risk_threat.level == RiskLevel.HIGH_RISK_SCAM
    assert "coercive_threat_scam" in risk_threat.flags

    # Clean text
    risk_safe = classifier.evaluate("Hello Manan, let's meet for lunch tomorrow.")
    assert risk_safe.level == RiskLevel.SAFE


def test_decision_engine_triage_actions() -> None:
    """Verify DecisionEngine produces correct actions for critical scenarios."""
    engine = DecisionEngine()

    # Scenario 1: Recruiter interview -> interrupt_user
    dec_interview = engine.evaluate(
        caller_id="+91-9988776655",
        utterance="Hello, I am calling from Microsoft HR regarding your interview tomorrow.",
    )
    assert dec_interview.recommended_action == AgentAction.INTERRUPT_USER
    assert dec_interview.requires_human_intervention is True

    # Scenario 2: Delivery partner -> handle_autonomously
    dec_del = engine.evaluate(
        caller_id="+91-9776655443",
        utterance="Zomato delivery boy at building gate.",
    )
    assert dec_del.recommended_action == AgentAction.HANDLE_AUTONOMOUSLY

    # Scenario 3: Extortion scam -> block_and_terminate
    dec_scam = engine.evaluate(
        caller_id="+91-9112233445",
        utterance="Police arrest warrant issued against your name.",
    )
    assert dec_scam.recommended_action == AgentAction.BLOCK_AND_TERMINATE
    assert dec_scam.should_terminate_call is True
