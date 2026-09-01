import re

from apps.agent.decision.models import CallIntent, IntentCategory


class IntentClassifier:
    """Classifies the primary intention and purpose of the call."""

    INTENT_RULES: list[tuple[re.Pattern, IntentCategory, str]] = [
        # Spam / Scam (Evaluated first to catch fraudulent threats)
        (
            re.compile(
                r"\b(lottery|won prize|won a lottery|claim 25 lakh|kyc blocked|account suspended|debit card pin|cvv|aadhaar otp|send otp|claim reward|arrest warrant|court summons|customs department|police warrant|penalty fee)\b",
                re.I,
            ),
            IntentCategory.SPAM_SCAM,
            "Suspected scam, phishing, or extortion attempt",
        ),
        # Job Interview & Recruitment
        (
            re.compile(
                r"\b(interview|round \d|shortlist|shortlisted|hiring|job role|application|resume|hr|offer letter|compensation|salary expectations|talent acquisition)\b",
                re.I,
            ),
            IntentCategory.JOB_INTERVIEW,
            "Job interview and recruitment discussion",
        ),
        # Delivery & Logistics
        (
            re.compile(
                r"\b(delivery|courier|package|parcel|zomato|swiggy|blinkit|zepto|amazon|gate pe|doorbell|otp bata|cash on delivery|cod)\b",
                re.I,
            ),
            IntentCategory.DELIVERY,
            "Package or food delivery inquiry",
        ),
        # Urgent Personal & Emergency
        (
            re.compile(
                r"\b(emergency|hospital|accident|tabiyat|doctor|police|urgent help|madad chahiye|serious|urgent matter)\b",
                re.I,
            ),
            IntentCategory.URGENT_PERSONAL,
            "Urgent personal or health emergency",
        ),
        # Work Collaboration & Engineering
        (
            re.compile(
                r"\b(github|pull request|pr|bug in production|jira|sprint|demo|deployment|database|code review|client meeting|client demo|figma)\b",
                re.I,
            ),
            IntentCategory.WORK_COLLABORATION,
            "Work collaboration and engineering task",
        ),
        # Utilities, Landlord & Maintenance
        (
            re.compile(
                r"\b(maintenance|landlord|rent|water supply|power backup|technician|plumber|electrician|ac service|broadband|electricity bill|gas meter|meter reading)\b",
                re.I,
            ),
            IntentCategory.UTILITY_MAINTENANCE,
            "Utility, housing, or maintenance coordination",
        ),
        # Sales & Marketing
        (
            re.compile(
                r"\b(pre-approved loan|credit card offer|insurance policy|invest in crypto|free gift card|buy property|trading scheme|real estate|luxury villas|investing in)\b",
                re.I,
            ),
            IntentCategory.SALES_MARKETING,
            "Sales and marketing promotion",
        ),
        # General Inquiry / Salutations
        (
            re.compile(
                r"\b(hello|namaste|hi|kaise ho|available to talk|free right now|kya kar rahe ho|call back|chai|party|gym|diwali|ghar kab)\b",
                re.I,
            ),
            IntentCategory.GENERAL_INQUIRY,
            "General inquiry or casual conversation",
        ),
    ]

    def classify(self, utterance: str) -> CallIntent:
        """Classify user speech into an IntentCategory with confidence and summary."""
        clean_text = utterance.strip()
        if not clean_text:
            return CallIntent(
                category=IntentCategory.UNKNOWN,
                confidence=0.0,
                summary="Empty utterance",
            )

        for pattern, category, summary in self.INTENT_RULES:
            match = pattern.search(clean_text)
            if match:
                matched_words = [match.group(0)]
                return CallIntent(
                    category=category,
                    confidence=0.88,
                    summary=summary,
                    key_entities=matched_words,
                )

        return CallIntent(
            category=IntentCategory.GENERAL_INQUIRY,
            confidence=0.50,
            summary="General conversation",
        )
