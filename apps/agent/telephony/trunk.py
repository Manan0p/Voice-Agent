"""SIP Trunking and Carrier Call Forwarding header resolution engine."""

import re
from typing import Any

from pydantic import BaseModel, Field

from packages.shared.logging import get_logger

logger = get_logger("apps.agent.telephony.trunk")


class TrunkConfig(BaseModel):
    """Configuration schema for an external SIP Trunk provider."""

    host: str = "trunk.provider.com"
    port: int = 5060
    user: str = "user"
    password: str = "pass"
    did_number: str = "+910000000000"
    provider_name: str = "Generic VoIP"
    use_tls: bool = False


class ResolvedCallerInfo(BaseModel):
    """Resolved identity and routing telemetry for an inbound telephony call."""

    caller_number: str
    is_forwarded: bool = False
    forwarded_from: str | None = None
    forwarding_reason: str | None = None
    is_owner: bool = False
    dialed_did: str | None = None
    raw_diversion: str | None = None
    raw_pai: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SIPHeaderParser:
    """Parses SIP signaling headers (Diversion, History-Info, PAI) to resolve true caller identities."""

    # Regex patterns for extracting numbers from SIP URIs
    SIP_URI_PHONE_PATTERN = re.compile(r"sip:([+0-9a-zA-Z]+)@", re.IGNORECASE)
    REASON_PATTERN = re.compile(r"reason=([a-zA-Z0-9_-]+)", re.IGNORECASE)

    @classmethod
    def normalize_phone_number(cls, raw: str | None) -> str:
        """Normalize raw telephony input to standard E.164-like phone string."""
        if not raw or not raw.strip():
            return "unknown"

        cleaned = raw.strip()

        # If it's a SIP URI, extract user portion
        match = cls.SIP_URI_PHONE_PATTERN.search(cleaned)
        if match:
            cleaned = match.group(1)

        # Remove common phone formatting characters
        cleaned = re.sub(r"[\s\-\(\)\.]", "", cleaned)

        # Retain leading + if present
        has_plus = cleaned.startswith("+")
        digits_only = re.sub(r"[^\d]", "", cleaned)

        if not digits_only:
            return "unknown"

        if has_plus:
            return f"+{digits_only}"

        # Standard Indian 10-digit number normalization: prefix with +91 if length is 10
        if len(digits_only) == 10:
            return f"+91{digits_only}"
        elif len(digits_only) == 12 and digits_only.startswith("91"):
            return f"+{digits_only}"

        return f"+{digits_only}"

    @classmethod
    def parse_diversion_header(cls, header: str | None) -> tuple[str | None, str | None]:
        """Parse SIP Diversion header (RFC 5806).

        Example: '<sip:+919876543210@carrier.com>;reason=unconditional'
        Returns (forwarded_from_number, forwarding_reason)
        """
        if not header or not header.strip():
            return None, None

        forwarded_from = None
        reason = None

        # Extract number
        match = cls.SIP_URI_PHONE_PATTERN.search(header)
        if match:
            forwarded_from = cls.normalize_phone_number(match.group(1))
        else:
            # Try raw digits inside angle brackets or start
            raw_match = re.search(r"<([+0-9]+)", header)
            if raw_match:
                forwarded_from = cls.normalize_phone_number(raw_match.group(1))

        # Extract reason
        reason_match = cls.REASON_PATTERN.search(header)
        if reason_match:
            reason = reason_match.group(1).lower()

        return forwarded_from, reason

    @classmethod
    def resolve_call(
        cls,
        caller_id_num: str | None,
        diversion_header: str | None = None,
        pai_header: str | None = None,
        dialed_did: str | None = None,
        owner_phone_number: str | None = None,
    ) -> ResolvedCallerInfo:
        """Determine whether call is direct, carrier-forwarded, or owner-initiated."""
        caller_norm = cls.normalize_phone_number(caller_id_num)
        owner_norm = cls.normalize_phone_number(owner_phone_number) if owner_phone_number else None
        did_norm = cls.normalize_phone_number(dialed_did) if dialed_did else None

        forwarded_from, reason = cls.parse_diversion_header(diversion_header)

        # Check if caller is the owner
        is_owner = bool(owner_norm and caller_norm == owner_norm)
        is_forwarded = bool(forwarded_from is not None)

        logger.info(
            "Resolved Call: Caller=%s, Forwarded=%s (From=%s, Reason=%s), IsOwner=%s, DID=%s",
            caller_norm,
            is_forwarded,
            forwarded_from,
            reason,
            is_owner,
            did_norm,
        )

        return ResolvedCallerInfo(
            caller_number=caller_norm,
            is_forwarded=is_forwarded,
            forwarded_from=forwarded_from,
            forwarding_reason=reason,
            is_owner=is_owner,
            dialed_did=did_norm,
            raw_diversion=diversion_header,
            raw_pai=pai_header,
        )
