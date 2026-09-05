"""Unit tests for AsteriskMediaBridge audio translation, framing, and queue management."""

import pytest
from pipecat.frames.frames import (
    InputAudioRawFrame,
    InterruptionFrame,
    OutputAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection

from apps.agent.telephony.asterisk_bridge import (
    AsteriskAudioInputProcessor,
    AsteriskAudioOutputProcessor,
    AsteriskMediaBridge,
)


@pytest.mark.asyncio
async def test_input_processor_push_audio_chunk() -> None:
    processor = AsteriskAudioInputProcessor(sample_rate=16000, num_channels=1)
    captured_frames = []

    async def mock_push_frame(frame, direction):
        captured_frames.append((frame, direction))

    processor.push_frame = mock_push_frame

    # 16kHz 16-bit mono: 320 samples = 640 bytes (20ms)
    pcm_data = b"\x00\x00" * 320
    await processor.push_audio_chunk(pcm_data)

    assert len(captured_frames) == 1
    frame, direction = captured_frames[0]
    assert isinstance(frame, InputAudioRawFrame)
    assert frame.audio == pcm_data
    assert frame.sample_rate == 16000
    assert frame.num_channels == 1
    assert direction == FrameDirection.DOWNSTREAM


@pytest.mark.asyncio
async def test_output_processor_queues_and_chunks_audio() -> None:
    # Target 16kHz, 20ms chunk = 640 bytes
    processor = AsteriskAudioOutputProcessor(target_sample_rate=16000, chunk_duration_ms=20)

    # 40ms of 16kHz audio = 1280 bytes (should split into 2 chunks of 640 bytes)
    pcm_data = b"\x01\x00" * 640
    frame = OutputAudioRawFrame(audio=pcm_data, sample_rate=16000, num_channels=1)

    await processor.process_frame(frame, FrameDirection.DOWNSTREAM)
    assert processor.is_speaking is True

    chunk1 = await processor.get_next_chunk(timeout=0.1)
    chunk2 = await processor.get_next_chunk(timeout=0.1)
    chunk3 = await processor.get_next_chunk(timeout=0.01)

    assert chunk1 is not None
    assert len(chunk1) == 640
    assert chunk2 is not None
    assert len(chunk2) == 640
    assert chunk3 is None  # Queue exhausted


@pytest.mark.asyncio
async def test_output_processor_interruption_flushing() -> None:
    processor = AsteriskAudioOutputProcessor(target_sample_rate=16000, chunk_duration_ms=20)

    pcm_data = b"\x01\x00" * 640
    frame = OutputAudioRawFrame(audio=pcm_data, sample_rate=16000, num_channels=1)
    await processor.process_frame(frame, FrameDirection.DOWNSTREAM)
    assert processor.is_speaking is True
    assert processor._outbound_queue.qsize() == 2

    # Receive InterruptionFrame
    interruption = InterruptionFrame()
    await processor.process_frame(interruption, FrameDirection.UPSTREAM)

    assert processor._outbound_queue.empty()
    assert processor.is_speaking is False


@pytest.mark.asyncio
async def test_asterisk_media_bridge_slin16_lifecycle() -> None:
    bridge = AsteriskMediaBridge(channel_id="chan-001", audio_format="slin16", sample_rate=16000)
    assert bridge.channel_id == "chan-001"
    assert bridge.audio_format == "slin16"

    # Send inbound audio
    inbound_pcm = b"\x00\x00" * 320
    await bridge.receive_inbound_audio(inbound_pcm)

    # Simulate outbound TTS output frame
    outbound_pcm = b"\x02\x00" * 320
    frame = OutputAudioRawFrame(audio=outbound_pcm, sample_rate=16000, num_channels=1)
    await bridge.output_processor.process_frame(frame, FrameDirection.DOWNSTREAM)

    chunk = await bridge.get_outbound_audio_chunk(timeout=0.1)
    assert chunk is not None
    assert len(chunk) == 640

    status = bridge.get_status()
    assert status["channel_id"] == "chan-001"
    assert status["format"] == "slin16"


@pytest.mark.asyncio
async def test_asterisk_media_bridge_ulaw_codec() -> None:
    bridge = AsteriskMediaBridge(channel_id="chan-002", audio_format="ulaw", sample_rate=16000)

    # 160 bytes of mu-law (20ms at 8kHz)
    ulaw_in = b"\xff" * 160
    await bridge.receive_inbound_audio(ulaw_in)

    # Produce outbound frame
    outbound_pcm = b"\x00\x00" * 320  # 640 bytes PCM
    frame = OutputAudioRawFrame(audio=outbound_pcm, sample_rate=16000, num_channels=1)
    await bridge.output_processor.process_frame(frame, FrameDirection.DOWNSTREAM)

    ulaw_out = await bridge.get_outbound_audio_chunk(timeout=0.1)
    assert ulaw_out is not None
    # 640 bytes PCM @ 16kHz -> 160 bytes ulaw @ 8kHz (20ms frame)
    assert len(ulaw_out) == 160
