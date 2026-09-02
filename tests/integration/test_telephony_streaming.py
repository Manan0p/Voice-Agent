import json
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from apps.agent.telephony.simulator import TelephonyCallSimulator
from apps.api.main import app
from packages.db.base import Base
from packages.db.session import get_async_session


@pytest.fixture
async def telephony_api_client() -> AsyncGenerator[AsyncClient, None]:
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
async def test_twilio_incoming_webhook_returns_twiml(telephony_api_client: AsyncClient) -> None:
    """Verify Twilio incoming call webhook generates TwiML Media Stream XML."""
    form_data = {
        "From": "+91-9876543210",
        "To": "+91-9999999999",
        "CallSid": "CA_test_call_123",
    }
    res = await telephony_api_client.post(
        "/api/telephony/twilio/incoming",
        data=form_data,
        headers={"host": "api.personal-agent.internal"},
    )
    assert res.status_code == 200
    assert "application/xml" in res.headers["content-type"]
    body = res.text
    assert "<Response>" in body
    assert '<Stream url="ws://api.personal-agent.internal/api/telephony/twilio/stream"/>' in body


@pytest.mark.asyncio
async def test_twilio_status_callback(telephony_api_client: AsyncClient) -> None:
    """Verify Twilio call status callback handler."""
    form_data = {
        "CallSid": "CA_test_call_123",
        "CallStatus": "completed",
        "CallDuration": "45",
    }
    res = await telephony_api_client.post("/api/telephony/twilio/status", data=form_data)
    assert res.status_code == 200
    assert res.json()["status"] == "received"


def test_twilio_bidirectional_websocket_stream() -> None:
    """Verify bidirectional audio streaming over WebSocket using simulated telephony client."""
    # Setup test database for synchronous Starlette TestClient WebSocket test
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async def init_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    import asyncio

    asyncio.run(init_tables())

    test_session_maker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_async_session():
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

    sim = TelephonyCallSimulator(
        call_sid="CA_live_test_001",
        stream_sid="MZ_live_test_001",
        caller_number="+91-9844455566",
    )

    with TestClient(app) as client:
        with client.websocket_connect("/api/telephony/twilio/stream") as websocket:
            # 1. Send Connected Event
            websocket.send_text(sim.create_connect_event())

            # 2. Send Start Event
            websocket.send_text(sim.create_start_event())

            # Receive initial greeting frames from agent
            greeting_msg = websocket.receive_text()
            parsed_greeting = json.loads(greeting_msg)
            assert parsed_greeting["event"] == "media"
            assert parsed_greeting["streamSid"] == sim.stream_sid

            # 3. Stream Simulated Caller Audio Frames
            audio_frames = sim.create_audio_frames_from_sine(duration_sec=0.1)
            for frame in audio_frames:
                websocket.send_text(frame)

            # 4. Send Stop Event
            websocket.send_text(sim.create_stop_event())

    app.dependency_overrides.clear()
