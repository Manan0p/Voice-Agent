import pytest
from pydantic import BaseModel

from apps.agent.structured.parser import extract_json_string, parse_structured


class SampleClassification(BaseModel):
    intent: str
    urgency_score: float
    is_spam: bool


def test_extract_json_markdown() -> None:
    """Verify extracting JSON enclosed in markdown code fences."""
    raw = 'Here is the analysis:\n```json\n{"intent": "personal", "urgency_score": 0.2, "is_spam": false}\n```'
    extracted = extract_json_string(raw)
    assert extracted == '{"intent": "personal", "urgency_score": 0.2, "is_spam": false}'


def test_extract_json_raw_braces() -> None:
    """Verify extracting JSON embedded in freeform conversational text."""
    raw = 'Based on the call, {"intent": "work", "urgency_score": 0.8, "is_spam": false} is the classification.'
    extracted = extract_json_string(raw)
    assert extracted == '{"intent": "work", "urgency_score": 0.8, "is_spam": false}'


def test_parse_structured_success() -> None:
    """Verify parsing valid text into a Pydantic schema."""
    raw = '```json\n{"intent": "interview", "urgency_score": 0.9, "is_spam": false}\n```'
    parsed = parse_structured(raw, SampleClassification)
    assert parsed.intent == "interview"
    assert parsed.urgency_score == 0.9
    assert parsed.is_spam is False


def test_parse_structured_invalid_raises() -> None:
    """Verify that malformed or non-matching JSON raises ValueError."""
    with pytest.raises(ValueError):
        parse_structured("No json here at all", SampleClassification)
