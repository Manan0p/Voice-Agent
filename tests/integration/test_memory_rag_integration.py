import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.db.base import Base
from packages.db.repositories import CallerMemoryRepository, KnowledgeRepository


@pytest.fixture
async def memory_db_session() -> AsyncSession:
    """Isolated database session fixture for integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_end_to_end_caller_memory_and_rag_pipeline(memory_db_session: AsyncSession) -> None:
    """Verify that multiple caller turns accumulate memory, persist messages, and query RAG knowledge."""
    caller_repo = CallerMemoryRepository(memory_db_session)
    knowledge_repo = KnowledgeRepository(memory_db_session)

    # 1. Populate RAG Knowledge Base
    vec_zoom = [0.8, 0.2] + [0.0] * 382
    await knowledge_repo.create_doc(
        title="Remote Meeting Preferences",
        category="calendar",
        content="Manan prefers Zoom or Google Meet links sent in calendar invites.",
        chunks=[
            (
                "Preferred video conferencing platforms are Zoom and Google Meet.",
                vec_zoom,
                {"type": "calendar"},
            ),
        ],
    )

    # 2. Turn 1: New Recruiter Calls
    call1 = await caller_repo.create_call(
        phone="+91-9988776652",
        status="active",
        intent="job_interview",
        urgency="high",
    )
    # Agent updates caller profile from dialogue
    await caller_repo.update_caller(
        phone="+91-9988776652",
        name="Priya",
        relationship="recruiter",
        organization="Microsoft",
        trust_score=0.75,
    )
    # Recruiter leaves message
    await caller_repo.save_message(
        caller_name="Priya",
        message="Interview scheduled for Friday. Please confirm preferred video platform.",
        phone_number="+91-9988776652",
        urgency="high",
        category="recruiter",
        call_id=call1.id,
    )
    await caller_repo.end_call(
        call_id=call1.id,
        duration_sec=60.0,
        summary="Priya from Microsoft scheduled interview and requested video platform",
    )

    # 3. Agent queries RAG to answer caller's video platform question
    rag_matches = await knowledge_repo.search_semantic(query_embedding=vec_zoom, top_k=1)
    assert len(rag_matches) == 1
    assert "Zoom and Google Meet" in rag_matches[0][0].chunk_text

    # 4. Turn 2: Follow-up Call from Same Recruiter
    caller_profile = await caller_repo.get_caller_by_phone("+91-9988776652")
    assert caller_profile is not None
    assert caller_profile.name == "Priya"
    assert caller_profile.organization == "Microsoft"
    assert caller_profile.relationship == "recruiter"

    history = await caller_repo.get_caller_history("+91-9988776652")
    assert len(history) == 1
    assert "Priya from Microsoft" in (history[0].summary or "")
