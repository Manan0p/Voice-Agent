import uuid
from datetime import UTC, datetime

from packages.db.models import (
    AgentAction,
    Call,
    Caller,
    KnowledgeChunk,
    KnowledgeDoc,
    Message,
    Reminder,
)


def test_caller_model_instantiation() -> None:
    """Verify Caller model fields and defaults."""
    caller_id = uuid.uuid4()
    caller = Caller(
        id=caller_id,
        phone_number="+91-9876543210",
        name="Manan",
        relationship="self",
        trust_score=1.0,
        organization="Owner",
        is_blocked=False,
    )

    assert caller.id == caller_id
    assert caller.phone_number == "+91-9876543210"
    assert caller.name == "Manan"
    assert caller.relationship == "self"
    assert caller.trust_score == 1.0
    assert caller.organization == "Owner"
    assert caller.is_blocked is False


def test_call_model_instantiation() -> None:
    """Verify Call model fields and relationships."""
    call_id = uuid.uuid4()
    caller_id = uuid.uuid4()
    now = datetime.now(UTC)

    call = Call(
        id=call_id,
        caller_id=caller_id,
        phone_number="+91-9811122233",
        status="completed",
        start_time=now,
        duration_sec=120.5,
        intent="urgent_personal",
        urgency="critical",
        summary="Emergency hospital call from Mummy",
    )

    assert call.id == call_id
    assert call.caller_id == caller_id
    assert call.phone_number == "+91-9811122233"
    assert call.duration_sec == 120.5
    assert call.intent == "urgent_personal"
    assert call.urgency == "critical"


def test_message_model_instantiation() -> None:
    """Verify Message model fields and defaults."""
    msg = Message(
        caller_name="Sneha",
        phone_number="+91-9844455566",
        message_content="Please review pull request #42 on GitHub.",
        urgency="high",
        category="work",
        is_read=False,
    )

    assert msg.caller_name == "Sneha"
    assert msg.phone_number == "+91-9844455566"
    assert msg.message_content == "Please review pull request #42 on GitHub."
    assert msg.urgency == "high"
    assert msg.category == "work"
    assert msg.is_read is False


def test_knowledge_and_chunk_model() -> None:
    """Verify KnowledgeDoc and KnowledgeChunk models."""
    doc_id = uuid.uuid4()
    doc = KnowledgeDoc(
        id=doc_id,
        title="Availability Guidelines",
        category="calendar",
        content="Available for meetings on weekdays between 2 PM and 6 PM IST.",
    )
    chunk = KnowledgeChunk(
        doc_id=doc_id,
        chunk_index=0,
        chunk_text="Available for meetings on weekdays between 2 PM and 6 PM IST.",
        embedding=[0.1] * 384,
    )

    assert doc.id == doc_id
    assert doc.title == "Availability Guidelines"
    assert chunk.doc_id == doc_id
    assert chunk.chunk_index == 0
    assert len(chunk.embedding or []) == 384


def test_reminder_model() -> None:
    """Verify Reminder model fields."""
    rem = Reminder(
        title="Follow up with Sneha",
        description="Discuss GitHub PR #42",
        is_completed=False,
    )
    assert rem.title == "Follow up with Sneha"
    assert rem.is_completed is False


def test_agent_action_audit_model() -> None:
    """Verify AgentAction model fields."""
    action = AgentAction(
        caller_id="+91-9876543210",
        tool_name="get_contact",
        arguments={"query": "Sneha"},
        success=True,
        data={"found": True},
        permission_level="read_only",
    )
    assert action.tool_name == "get_contact"
    assert action.success is True
    assert action.permission_level == "read_only"
