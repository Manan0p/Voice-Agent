"""Unit tests for SIPHeaderParser, phone normalization, Diversion headers, and TrunkConfig."""

from apps.agent.telephony.trunk import (
    SIPHeaderParser,
    TrunkConfig,
)


def test_normalize_phone_number_e164() -> None:
    # 10-digit Indian numbers
    assert SIPHeaderParser.normalize_phone_number("9876543210") == "+919876543210"
    assert SIPHeaderParser.normalize_phone_number("+91 98765-43210") == "+919876543210"
    assert SIPHeaderParser.normalize_phone_number("(+91) 98765 43210") == "+919876543210"

    # Full E.164
    assert SIPHeaderParser.normalize_phone_number("+14155552671") == "+14155552671"
    assert SIPHeaderParser.normalize_phone_number("+442071838750") == "+442071838750"

    # SIP URI format
    assert (
        SIPHeaderParser.normalize_phone_number("sip:+919876543210@carrier.com") == "+919876543210"
    )
    assert SIPHeaderParser.normalize_phone_number("<sip:9876543210@trunk.net>") == "+919876543210"

    # Empty / None
    assert SIPHeaderParser.normalize_phone_number("") == "unknown"
    assert SIPHeaderParser.normalize_phone_number(None) == "unknown"


def test_parse_diversion_header_unconditional() -> None:
    header = "<sip:+919876543210@carrier.com>;reason=unconditional;counter=1"
    forwarded_from, reason = SIPHeaderParser.parse_diversion_header(header)
    assert forwarded_from == "+919876543210"
    assert reason == "unconditional"


def test_parse_diversion_header_user_busy() -> None:
    header = "<sip:919876543210@ims.mnc001.mcc404.3gppnetwork.org>;reason=user-busy"
    forwarded_from, reason = SIPHeaderParser.parse_diversion_header(header)
    assert forwarded_from == "+919876543210"
    assert reason == "user-busy"


def test_parse_diversion_header_none_or_empty() -> None:
    assert SIPHeaderParser.parse_diversion_header(None) == (None, None)
    assert SIPHeaderParser.parse_diversion_header("") == (None, None)
    assert SIPHeaderParser.parse_diversion_header("   ") == (None, None)


def test_resolve_call_direct_incoming() -> None:
    resolved = SIPHeaderParser.resolve_call(
        caller_id_num="+911122334455",
        diversion_header=None,
        dialed_did="+910000000000",
        owner_phone_number="+919876543210",
    )
    assert resolved.caller_number == "+911122334455"
    assert resolved.is_forwarded is False
    assert resolved.forwarded_from is None
    assert resolved.is_owner is False
    assert resolved.dialed_did == "+910000000000"


def test_resolve_call_carrier_forwarded() -> None:
    diversion = "<sip:+919876543210@jio.carrier.in>;reason=no-answer"
    resolved = SIPHeaderParser.resolve_call(
        caller_id_num="+911122334455",
        diversion_header=diversion,
        dialed_did="+910000000000",
        owner_phone_number="+919876543210",
    )
    assert resolved.caller_number == "+911122334455"
    assert resolved.is_forwarded is True
    assert resolved.forwarded_from == "+919876543210"
    assert resolved.forwarding_reason == "no-answer"
    assert resolved.is_owner is False


def test_resolve_call_owner_direct() -> None:
    resolved = SIPHeaderParser.resolve_call(
        caller_id_num="+919876543210",
        diversion_header=None,
        dialed_did="+910000000000",
        owner_phone_number="+919876543210",
    )
    assert resolved.caller_number == "+919876543210"
    assert resolved.is_forwarded is False
    assert resolved.is_owner is True


def test_trunk_config_model() -> None:
    config = TrunkConfig(
        host="sip.telnyx.com",
        port=5060,
        user="my_trunk_user",
        password="my_trunk_password",
        did_number="+918000000000",
        provider_name="Telnyx",
    )
    assert config.host == "sip.telnyx.com"
    assert config.provider_name == "Telnyx"
    assert config.use_tls is False
