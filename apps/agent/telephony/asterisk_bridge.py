"""Asterisk Media Bridge for bidirectional real-time audio transport with Pipecat pipeline."""

import asyncio
from typing import Any

import numpy as np
from pipecat.frames.frames import (
    CancelFrame,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    OutputAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from apps.agent.telephony.codecs import (
    chunk_audio,
    mulaw_to_pcm16_bytes,
    pcm_to_mulaw_bytes,
)
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.telephony.asterisk_bridge")


class AsteriskAudioInputProcessor(FrameProcessor):
    """Source processor that pushes Asterisk inbound audio frames into the Pipecat pipeline."""

    def __init__(self, sample_rate: int = 16000, num_channels: int = 1) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.num_channels = num_channels

    async def push_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Push raw PCM16 audio bytes from Asterisk into the pipeline."""
        if not pcm_bytes:
            return
        frame = InputAudioRawFrame(
            audio=pcm_bytes,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels,
        )
        await self.push_frame(frame, FrameDirection.DOWNSTREAM)


class AsteriskAudioOutputProcessor(FrameProcessor):
    """Sink processor that receives synthesized TTS audio frames and queues them for Asterisk playback."""

    def __init__(
        self,
        target_sample_rate: int = 16000,
        chunk_duration_ms: int = 20,
    ) -> None:
        super().__init__()
        self.target_sample_rate = target_sample_rate
        self.chunk_size = int(
            target_sample_rate * (chunk_duration_ms / 1000.0) * 2
        )  # 16-bit = 2 bytes/sample
        self._outbound_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.is_speaking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process frames flowing through the pipeline."""
        await super().process_frame(frame, direction)

        if isinstance(frame, (InterruptionFrame, CancelFrame)):
            logger.info("Asterisk audio playback interrupted — flushing queue.")
            self.clear_outbound_queue()
            self.is_speaking = False
            await self.push_frame(frame, direction)

        elif isinstance(frame, OutputAudioRawFrame):
            self.is_speaking = True
            audio_bytes = frame.audio
            src_rate = frame.sample_rate

            # Resample to target rate (16kHz) if needed
            if src_rate != self.target_sample_rate and len(audio_bytes) > 0:
                audio_bytes = self._resample_pcm16(audio_bytes, src_rate, self.target_sample_rate)

            # Chunk into 20ms frames and enqueue
            chunks = chunk_audio(audio_bytes, chunk_size_bytes=self.chunk_size)
            for chunk in chunks:
                await self._outbound_queue.put(chunk)

            await self.push_frame(frame, direction)

    def _resample_pcm16(self, audio_bytes: bytes, src_rate: int, dst_rate: int) -> bytes:
        """Resample 16-bit linear PCM audio using numpy linear interpolation."""
        try:
            samples = np.frombuffer(audio_bytes, dtype=np.int16)
            if len(samples) == 0:
                return audio_bytes
            duration = len(samples) / float(src_rate)
            num_dst_samples = int(duration * dst_rate)
            if num_dst_samples == 0:
                return audio_bytes
            orig_indices = np.linspace(0, len(samples) - 1, num=len(samples))
            new_indices = np.linspace(0, len(samples) - 1, num=num_dst_samples)
            resampled = np.interp(new_indices, orig_indices, samples).astype(np.int16)
            return resampled.tobytes()
        except Exception as e:
            logger.warning("Error resampling Asterisk audio: %s", e)
            return audio_bytes

    def clear_outbound_queue(self) -> None:
        """Clear queued audio immediately upon interruption/barge-in."""
        while not self._outbound_queue.empty():
            try:
                self._outbound_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self.is_speaking = False

    async def get_next_chunk(self, timeout: float = 0.05) -> bytes | None:
        """Retrieve next 20ms audio chunk for Asterisk playback."""
        try:
            return await asyncio.wait_for(self._outbound_queue.get(), timeout=timeout)
        except TimeoutError:
            self.is_speaking = False
            return None


class AsteriskMediaBridge:
    """Manages audio translation, codec handling, and streaming between Asterisk and Pipecat."""

    def __init__(
        self,
        channel_id: str,
        audio_format: str = "slin16",
        sample_rate: int = 16000,
    ) -> None:
        self.channel_id = channel_id
        self.audio_format = audio_format.lower()
        self.sample_rate = sample_rate

        self.input_processor = AsteriskAudioInputProcessor(sample_rate=sample_rate)
        self.output_processor = AsteriskAudioOutputProcessor(target_sample_rate=sample_rate)

    async def receive_inbound_audio(self, raw_audio: bytes) -> None:
        """Feed inbound audio from Asterisk into the Pipecat input processor."""
        if not raw_audio:
            return

        pcm_bytes = raw_audio
        if self.audio_format in ("ulaw", "g711u", "mulaw"):
            pcm_bytes = mulaw_to_pcm16_bytes(raw_audio, target_sample_rate=self.sample_rate)

        await self.input_processor.push_audio_chunk(pcm_bytes)

    async def get_outbound_audio_chunk(self, timeout: float = 0.05) -> bytes | None:
        """Fetch next synthesized audio chunk formatted for Asterisk."""
        chunk = await self.output_processor.get_next_chunk(timeout=timeout)
        if chunk is None:
            return None

        if self.audio_format in ("ulaw", "g711u", "mulaw"):
            return pcm_to_mulaw_bytes(chunk, source_sample_rate=self.sample_rate)
        return chunk

    def handle_barge_in(self) -> None:
        """Signal barge-in interruption to flush active playback buffer."""
        self.output_processor.clear_outbound_queue()

    def get_status(self) -> dict[str, Any]:
        """Return bridge diagnostic status."""
        return {
            "channel_id": self.channel_id,
            "format": self.audio_format,
            "sample_rate": self.sample_rate,
            "is_speaking": self.output_processor.is_speaking,
            "queue_size": self.output_processor._outbound_queue.qsize(),
        }
