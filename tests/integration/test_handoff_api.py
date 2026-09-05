"""Integration tests for Human Handoff REST API endpoints."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.agent.telephony.asterisk_ari import AsteriskARIClient
from apps.agent.telephony.handoff import HandoffManager, get_handoff_manager
from apps.api.main import app
from packages.db.base import Base
from packages.db.session import get_async_session
from packages.schemas.asterisk import AsteriskBridge
from packages.schemas.handoff import HandoffState


@pytest.fixture
def mock_ari_client() -> AsteriskARIClient:
    client = AsteriskARIClient()
    client.create_bridge = AsyncMock(
        return_value=AsteriskBridge(
            id="bridge-api-123",
            technology="simple_bridge",
            bridge_type="mixing",
            name="handoff_bridge_call-api-01",
        )
    )
    client.add_channel_to_bridge = AsyncMock(return_value=True)
    client.remove_channel_from_bridge = AsyncMock(return_value=True)
    client.hangup_channel = AsyncMock(return_value=True)
    return client


@pytest.fixture
async def handoff_api_client(
    mock_ari_client: AsteriskARIClient,
) -> AsyncGenerator[tuple[AsyncClient, HandoffManager], None]:
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

    manager = HandoffManager(ari_client=mock_ari_client)

    app.dependency_overrides[get_async_session] = override_get_async_session
    app.dependency_overrides[get_handoff_manager] = lambda: manager

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, manager

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_handoff_api_take_call(
    handoff_api_client: tuple[AsyncClient, HandoffManager],
) -> None:
    client, manager = handoff_api_client
    manager.register_call("call-api-01", caller_phone="+919876543210")

    # 1. Check initial status
    res_status = await client.get("/api/calls/call-api-01/handoff/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["state"] == HandoffState.AI_HANDLING.value

    # 2. Take Call
    res_take = await client.post(
        "/api/calls/call-api-01/handoff/take",
        json={
            "action": "take_call",
            "target_endpoint": "PJSIP/1002",
            "reason": "VIP Caller",
        },
    )
    assert res_take.status_code == 200
    data_take = res_take.json()
    assert data_take["success"] is True
    assert data_take["current_state"] == HandoffState.HUMAN_HANDLING.value
    assert data_take["bridge_id"] == "bridge-api-123"

    # 3. Verify status changed to HUMAN_HANDLING
    res_status_after = await client.get("/api/calls/call-api-01/handoff/status")
    assert res_status_after.status_code == 200
    assert res_status_after.json()["state"] == HandoffState.HUMAN_HANDLING.value


@pytest.mark.asyncio
async def test_handoff_api_keep_ai(
    handoff_api_client: tuple[AsyncClient, HandoffManager],
) -> None:
    client, manager = handoff_api_client
    manager.register_call("call-api-02", caller_phone="+911122334455")

    res = await client.post(
        "/api/calls/call-api-02/handoff/keep-ai",
        json={"action": "keep_ai", "reason": "Not urgent"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["current_state"] == HandoffState.AI_HANDLING.value


@pytest.mark.asyncio
async def test_handoff_api_resume_ai_and_end(
    handoff_api_client: tuple[AsyncClient, HandoffManager],
) -> None:
    client, manager = handoff_api_client
    session = manager.register_call("call-api-03", caller_phone="+911122334455")
    session.state = HandoffState.HUMAN_HANDLING
    session.bridge_id = "bridge-api-123"

    # 1. Resume AI
    res_resume = await client.post(
        "/api/calls/call-api-03/handoff/resume-ai",
        json={"action": "resume_ai", "reason": "Done talking"},
    )
    assert res_resume.status_code == 200
    assert res_resume.json()["current_state"] == HandoffState.AI_RESUMED.value

    # 2. End Call
    res_end = await client.post(
        "/api/calls/call-api-03/handoff/end",
        json={"action": "end_call", "reason": "Finished call"},
    )
    assert res_end.status_code == 200
    assert res_end.json()["current_state"] == HandoffState.COMPLETED.value
