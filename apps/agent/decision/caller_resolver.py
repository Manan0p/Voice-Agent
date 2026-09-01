import re

from apps.agent.decision.models import CallerIdentity, CallerRelationship


class CallerResolver:
    """Resolves caller identity, relationship, and organization from phone ID and speech context."""

    DEFAULT_CONTACTS: dict[str, dict[str, str | CallerRelationship | float]] = {
        "+91-9876543210": {
            "name": "Manan",
            "relationship": CallerRelationship.SELF,
            "trust": 1.0,
        },
        "+91-9811122233": {
            "name": "Mummy",
            "relationship": CallerRelationship.FAMILY,
            "trust": 1.0,
        },
        "+91-9822233344": {
            "name": "Papa",
            "relationship": CallerRelationship.FAMILY,
            "trust": 1.0,
        },
        "+91-9833344455": {
            "name": "Rahul",
            "relationship": CallerRelationship.FRIEND,
            "trust": 0.85,
        },
        "+91-9844455566": {
            "name": "Sneha",
            "relationship": CallerRelationship.COLLEAGUE,
            "trust": 0.85,
        },
    }

    # Relationship patterns in speech (prioritized by specificity)
    RELATIONSHIP_PATTERNS: list[tuple[re.Pattern, CallerRelationship, float]] = [
        # Scam & Spam indicators first
        (
            re.compile(
                r"\b(police warrant|customs department|arrest warrant|court summons|won a lottery|claim 25 lakh|kyc blocked|account suspended)\b",
                re.I,
            ),
            CallerRelationship.SPAM,
            0.0,
        ),
        (
            re.compile(
                r"\b(credit card offer|pre-approved loan|investment in crypto|real estate offer|free gift card|sales team)\b",
                re.I,
            ),
            CallerRelationship.SPAM,
            0.20,
        ),
        # Recruiter & Talent Acquisition
        (
            re.compile(
                r"\b(hr|recruiter|recruitment|talent acquire|talent acquisition|hiring manager|technical interview|job offer|resume shortlist|shortlisted)\b",
                re.I,
            ),
            CallerRelationship.RECRUITER,
            0.75,
        ),
        # Delivery & Logistics
        (
            re.compile(
                r"\b(zomato|swiggy|blinkit|zepto|amazon courier|blue dart|courier delivery|parcel delivery|delivery boy|delivery partner)\b",
                re.I,
            ),
            CallerRelationship.DELIVERY,
            0.70,
        ),
        # Family
        (
            re.compile(
                r"\b(mummy|mother|mom|papa|father|dad|bhaiya|didi|sister|brother|uncle|aunt|beta)\b",
                re.I,
            ),
            CallerRelationship.FAMILY,
            0.95,
        ),
        # Colleagues & Engineering
        (
            re.compile(
                r"\b(github|pull request|jira ticket|sprint demo|production down|p0 bug|database crash|office team|colleague|client demo|demo meeting)\b",
                re.I,
            ),
            CallerRelationship.COLLEAGUE,
            0.80,
        ),
        # Business / Utilities / Landlords
        (
            re.compile(
                r"\b(landlord|society maintenance|ac service technician|plumber|electrician|broadband service|electricity bill|gas meter|meter reading)\b",
                re.I,
            ),
            CallerRelationship.BUSINESS,
            0.70,
        ),
        # Friends
        (
            re.compile(
                r"\b(arre manan|arre bhai|chai pe|weekend trip|party celebrate|gym chalna)\b",
                re.I,
            ),
            CallerRelationship.FRIEND,
            0.80,
        ),
    ]

    def __init__(self, contact_book: dict[str, dict] | None = None) -> None:
        self.contacts = contact_book or self.DEFAULT_CONTACTS.copy()

    def resolve(
        self,
        caller_id: str,
        initial_name: str | None = None,
        utterance: str | None = None,
    ) -> CallerIdentity:
        """Resolve caller profile by cross-referencing contact registry and utterance context."""
        # 1. Exact contact match
        if caller_id in self.contacts:
            contact = self.contacts[caller_id]
            return CallerIdentity(
                caller_id=caller_id,
                caller_name=str(contact["name"]),
                relationship=CallerRelationship(contact["relationship"]),
                trust_score=float(contact["trust"]),
                is_known_contact=True,
            )

        # 2. Extract self-introduction from utterance if available
        name = initial_name
        relationship = CallerRelationship.UNKNOWN
        trust_score = 0.5
        org = None

        if utterance:
            # Check for name patterns: "I am Priya", "This is Sneha from TechCorp", "Main Rahul bol raha hoon"
            name_match = re.search(
                r"\b(?:this is|i am|main|naam)\s+([A-Z][a-z]+)\b", utterance, re.I
            )
            if name_match and not name:
                name = name_match.group(1).capitalize()

            # Check for organization: "from TechCorp", "from Google", "from Microsoft"
            org_match = re.search(r"\bfrom\s+([A-Z][a-zA-Z0-9]+)\b", utterance, re.I)
            if org_match:
                org = org_match.group(1)

            # Match relationship patterns
            for pattern, rel, score in self.RELATIONSHIP_PATTERNS:
                if pattern.search(utterance):
                    relationship = rel
                    trust_score = score
                    break

        return CallerIdentity(
            caller_id=caller_id,
            caller_name=name,
            relationship=relationship,
            organization=org,
            trust_score=trust_score,
            is_known_contact=bool(name and relationship != CallerRelationship.UNKNOWN),
        )
