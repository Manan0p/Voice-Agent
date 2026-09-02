import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.db.base import Base
from packages.db.repositories import (
    ActionAuditRepository,
    CallerMemoryRepository,
    KnowledgeRepository,
)


@pytest.fixture
async def test_session() -> AsyncSession:
    """Create an isolated in-memory SQLite database session for unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_caller_memory_repository_crud(test_session: AsyncSession) -> None:
    """Verify CallerMemoryRepository caller creation, update, and history retrieval."""
    repo = CallerMemoryRepository(test_session)

    # 1. Create / retrieve caller
    caller = await repo.get_or_create_caller(
        phone="+91-9811122233",
        name="Mummy",
        relationship="family",
        trust_score=1.0,
    )
    assert caller.name == "Mummy"
    assert caller.relationship == "family"

    # 2. Update caller
    updated = await repo.update_caller(
        phone="+91-9811122233",
        notes="Preferred call time: evening after 7 PM",
    )
    assert updated is not None
    assert updated.notes == "Preferred call time: evening after 7 PM"

    # 3. Create call session
    call = await repo.create_call(
        phone="+91-9811122233",
        intent="urgent_personal",
        urgency="critical",
    )
    assert call.phone_number == "+91-9811122233"
    assert call.intent == "urgent_personal"

    # 4. End call
    ended_call = await repo.end_call(
        call_id=call.id,
        duration_sec=85.0,
        summary="Mummy called about hospital emergency",
        transcript=[{"speaker": "Mummy", "text": "Beta emergency hai"}],
    )
    assert ended_call is not None
    assert ended_call.duration_sec == 85.0
    assert ended_call.status == "completed"

    # 5. Save message
    msg = await repo.save_message(
        caller_name="Mummy",
        message="Please call back immediately",
        phone_number="+91-9811122233",
        urgency="critical",
        category="emergency",
        call_id=call.id,
    )
    assert msg.caller_name == "Mummy"
    assert msg.urgency == "critical"

    # 6. Retrieve history & unread messages
    history = await repo.get_caller_history(phone="+91-9811122233")
    assert len(history) == 1
    assert history[0].id == call.id

    unread = await repo.get_unread_messages()
    assert len(unread) == 1
    assert unread[0].id == msg.id


@pytest.mark.asyncio
async def test_knowledge_repository_semantic_search(test_session: AsyncSession) -> None:
    """Verify KnowledgeRepository document creation, chunking, and semantic vector similarity search."""
    repo = KnowledgeRepository(test_session)

    # Embedding vectors (384-dimensional simulated unit vectors)
    vec_calendar = [1.0] + [0.0] * 383
    vec_project = [0.0, 1.0] + [0.0] * 382

    doc = await repo.create_doc(
        title="Personal Meeting Guide",
        category="calendar",
        content="Manan is available on weekdays between 2 PM and 6 PM IST.",
        chunks=[
            (
                "Manan is available on weekdays between 2 PM and 6 PM IST for meetings.",
                vec_calendar,
                {"topic": "meeting_schedule"},
            ),
            (
                "Mornings are reserved for deep coding and project engineering.",
                vec_project,
                {"topic": "morning_focus"},
            ),
        ],
    )
    assert doc.title == "Personal Meeting Guide"

    # Search with query vector close to calendar
    query_vec = [0.98, 0.02] + [0.0] * 382
    results = await repo.search_semantic(query_embedding=query_vec, top_k=1)
    assert len(results) == 1
    top_chunk, score = results[0]
    assert "weekdays between 2 PM and 6 PM" in top_chunk.chunk_text
    assert score > 0.80

    # Keyword text search
    text_results = await repo.search_text(query="deep coding")
    assert len(text_results) >= 1
    assert "deep coding" in text_results[0].chunk_text


@pytest.mark.asyncio
async def test_action_audit_repository(test_session: AsyncSession) -> None:
    """Verify ActionAuditRepository logs tool execution and queries audit history."""
    repo = ActionAuditRepository(test_session)

    # Log action
    action = await repo.log_action(
        caller_id="+91-9876543210",
        tool_name="get_contact",
        arguments={"query": "Sneha"},
        success=True,
        data={"found": True, "name": "Sneha"},
        permission_level="read_only",
    )
    assert action.tool_name == "get_contact"
    assert action.success is True

    # Retrieve recent actions
    recent = await repo.get_recent_actions(limit=10)
    assert len(recent) >= 1
    assert recent[0].id == action.id
