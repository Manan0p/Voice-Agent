import re

from apps.agent.decision.models import RiskAssessment, RiskLevel


class RiskClassifier:
    """Detects security violations, credential phishing, and fraudulent scam patterns."""

    CREDENTIAL_PATTERNS = [
        (
            re.compile(
                r"\b(otp|one time password|verification code|pin|cvv|password|passcode)\b", re.I
            ),
            "credential_request",
        ),
        (
            re.compile(
                r"\b(bank account number|debit card number|credit card number|netbanking)\b", re.I
            ),
            "financial_data_request",
        ),
    ]

    SCAM_THREAT_PATTERNS = [
        (
            re.compile(
                r"\b(police warrant|customs seizure|narcotics department|cbi officer|arrest warrant|court summons)\b",
                re.I,
            ),
            "coercive_threat_scam",
        ),
        (
            re.compile(
                r"\b(won a lottery|claim 25 lakh|send processing fee|crypto investment double)\b",
                re.I,
            ),
            "financial_scam",
        ),
    ]

    def evaluate(self, utterance: str) -> RiskAssessment:
        """Analyze text for phishing, social engineering, and security risks."""
        clean_text = utterance.strip()
        if not clean_text:
            return RiskAssessment(
                level=RiskLevel.SAFE,
                score=0.0,
                requested_sensitive_info=False,
                flags=[],
                reason="Clean input",
            )

        flags: list[str] = []
        is_credential = False
        is_high_risk = False

        for pattern, flag in self.CREDENTIAL_PATTERNS:
            if pattern.search(clean_text):
                flags.append(flag)
                is_credential = True

        for pattern, flag in self.SCAM_THREAT_PATTERNS:
            if pattern.search(clean_text):
                flags.append(flag)
                is_high_risk = True

        if is_high_risk:
            return RiskAssessment(
                level=RiskLevel.HIGH_RISK_SCAM,
                score=0.95,
                requested_sensitive_info=is_credential,
                flags=flags,
                reason="Coercive authority impersonation or predatory financial scam detected",
            )

        if is_credential:
            return RiskAssessment(
                level=RiskLevel.CREDENTIAL_FISHING,
                score=0.85,
                requested_sensitive_info=True,
                flags=flags,
                reason="Caller requested sensitive authentication credentials (OTP/PIN/password)",
            )

        if len(flags) > 0:
            return RiskAssessment(
                level=RiskLevel.SUSPICIOUS,
                score=0.50,
                requested_sensitive_info=False,
                flags=flags,
                reason="Suspicious conversational patterns detected",
            )

        return RiskAssessment(
            level=RiskLevel.SAFE,
            score=0.0,
            requested_sensitive_info=False,
            flags=[],
            reason="No security risks identified",
        )
