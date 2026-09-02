import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.main import app
from packages.db.base import Base
from packages.db.session import get_async_session


@pytest.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client with isolated in-memory database session override."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_async_session] = override_get_async_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_health_and_root_endpoints(api_client: AsyncClient) -> None:
    """Verify health and root endpoints."""
    res_health = await api_client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_root = await api_client.get("/")
    assert res_root.status_code == 200
    assert "version" in res_root.json()


@pytest.mark.asyncio
async def test_contacts_crud_and_search(api_client: AsyncClient) -> None:
    """Verify Contact creation, search, retrieval, update, and deletion."""
    # 1. Create Contact
    contact_data = {
        "phone_number": "+91-9844455566",
        "name": "Sneha",
        "relationship": "colleague",
        "organization": "TechCorp",
        "trust_score": 0.85,
    }
    res_post = await api_client.post("/api/contacts", json=contact_data)
    assert res_post.status_code == 201
    contact = res_post.json()
    contact_id = contact["id"]
    assert contact["name"] == "Sneha"

    # 2. List & Search
    res_list = await api_client.get("/api/contacts?q=Sneha")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Sneha"

    # 3. Get Contact by ID
    res_get = await api_client.get(f"/api/contacts/{contact_id}")
    assert res_get.status_code == 200
    assert res_get.json()["phone_number"] == "+91-9844455566"

    # 4. Update Contact
    res_put = await api_client.put(
        f"/api/contacts/{contact_id}",
        json={"notes": "Available on Slack"},
    )
    assert res_put.status_code == 200
    assert res_put.json()["notes"] == "Available on Slack"

    # 5. Delete Contact
    res_del = await api_client.delete(f"/api/contacts/{contact_id}")
    assert res_del.status_code == 204

    # 6. Verify 404 after deletion
    res_404 = await api_client.get(f"/api/contacts/{contact_id}")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_calls_lifecycle_and_filters(api_client: AsyncClient) -> None:
    """Verify Call session creation, filtering, detail inspection, and updating."""
    # 1. Create Call
    call_data = {
        "phone_number": "+91-9811122233",
        "status": "active",
        "intent": "urgent_personal",
        "urgency": "critical",
    }
    res_post = await api_client.post("/api/calls", json=call_data)
    assert res_post.status_code == 201
    call = res_post.json()
    call_id = call["id"]
    assert call["intent"] == "urgent_personal"

    # 2. List with filters
    res_list = await api_client.get("/api/calls?phone_number=%2B91-9811122233&status=active")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == call_id

    # 3. Update Call (complete call)
    res_patch = await api_client.patch(
        f"/api/calls/{call_id}",
        json={
            "status": "completed",
            "duration_sec": 75.5,
            "summary": "Mummy reported urgent emergency",
            "transcript": [{"speaker": "Mummy", "text": "Beta hospital emergency hai"}],
        },
    )
    assert res_patch.status_code == 200
    updated = res_patch.json()
    assert updated["status"] == "completed"
    assert updated["duration_sec"] == 75.5

    # 4. Get Detail
    res_detail = await api_client.get(f"/api/calls/{call_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert len(detail["transcript"]) == 1


@pytest.mark.asyncio
async def test_messages_lifecycle(api_client: AsyncClient) -> None:
    """Verify Voicemail/Message creation, listing, read status update, and deletion."""
    # 1. Create Message
    msg_data = {
        "caller_name": "Priya",
        "phone_number": "+91-9988776652",
        "message": "Calling from Microsoft HR regarding scheduled interview.",
        "urgency": "high",
        "category": "recruiter",
    }
    res_post = await api_client.post("/api/messages", json=msg_data)
    assert res_post.status_code == 201
    msg = res_post.json()
    msg_id = msg["id"]
    assert msg["is_read"] is False

    # 2. List unread messages
    res_list = await api_client.get("/api/messages?is_read=false&urgency=high")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] == 1
    assert data["items"][0]["caller_name"] == "Priya"

    # 3. Mark as read
    res_patch = await api_client.patch(f"/api/messages/{msg_id}", json={"is_read": True})
    assert res_patch.status_code == 200
    assert res_patch.json()["is_read"] is True

    # 4. Delete message
    res_del = await api_client.delete(f"/api/messages/{msg_id}")
    assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_knowledge_and_search_endpoints(api_client: AsyncClient) -> None:
    """Verify Knowledge document ingestion and search endpoints."""
    # 1. Create Knowledge Doc
    doc_data = {
        "title": "Interview Availability",
        "category": "calendar",
        "content": "Manan is available for interviews on weekdays between 2 PM and 6 PM IST.",
    }
    res_post = await api_client.post("/api/knowledge", json=doc_data)
    assert res_post.status_code == 201
    doc = res_post.json()
    doc_id = doc["id"]

    # 2. Search Knowledge
    res_search = await api_client.post(
        "/api/knowledge/search",
        json={"query": "interviews availability", "category": "calendar"},
    )
    assert res_search.status_code == 200
    results = res_search.json()
    assert len(results) >= 1
    assert "weekdays between 2 PM and 6 PM" in results[0]["chunk_text"]

    # 3. Delete Knowledge Doc
    res_del = await api_client.delete(f"/api/knowledge/{doc_id}")
    assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_reminders_endpoints(api_client: AsyncClient) -> None:
    """Verify Reminder creation, completion toggle, and deletion."""
    # 1. Create Reminder
    rem_data = {
        "title": "Review GitHub PR",
        "description": "Check pull request #42 from Sneha",
    }
    res_post = await api_client.post("/api/reminders", json=rem_data)
    assert res_post.status_code == 201
    rem = res_post.json()
    rem_id = rem["id"]
    assert rem["is_completed"] is False

    # 2. Mark complete
    res_patch = await api_client.patch(f"/api/reminders/{rem_id}/complete?completed=true")
    assert res_patch.status_code == 200
    assert res_patch.json()["is_completed"] is True

    # 3. Delete reminder
    res_del = await api_client.delete(f"/api/reminders/{rem_id}")
    assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_system_status_endpoint(api_client: AsyncClient) -> None:
    """Verify System Status overview endpoint."""
    res = await api_client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["database_connected"] is True
    assert len(data["components"]) >= 4
    assert "faster-whisper" in data["stt_model"]
    assert "kokoro" in data["tts_engine"].lower()


@pytest.mark.asyncio
async def test_not_found_handling(api_client: AsyncClient) -> None:
    """Verify structured 404 responses for non-existent entities."""
    fake_id = str(uuid.uuid4())
    res_call = await api_client.get(f"/api/calls/{fake_id}")
    assert res_call.status_code == 404

    res_msg = await api_client.get(f"/api/messages/{fake_id}")
    assert res_msg.status_code == 404

    res_contact = await api_client.get(f"/api/contacts/{fake_id}")
    assert res_contact.status_code == 404
