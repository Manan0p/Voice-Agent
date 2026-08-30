import time

import numpy as np
from pipecat.frames.frames import (
    CancelFrame,
    Frame,
    InterruptionFrame,
    TextFrame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from apps.agent.tts.base import TTSProvider
from apps.agent.tts.factory import get_tts_provider
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.voice.tts_service")


class KokoroTTSService(FrameProcessor):
    """Pipecat FrameProcessor synthesizing TextFrames into TTSAudioRawFrames using Kokoro-82M."""

    def __init__(
        self,
        tts_provider: TTSProvider | None = None,
        sample_rate: int = 24000,
        chunk_size_samples: int = 480,  # 20ms @ 24kHz
    ) -> None:
        super().__init__()
        self.tts = tts_provider or get_tts_provider()
        self.sample_rate = sample_rate
        self.chunk_size_samples = chunk_size_samples
        self._interrupted = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process incoming frames and stream synthesized audio frames."""
        await super().process_frame(frame, direction)

        if isinstance(frame, (InterruptionFrame, CancelFrame)):
            self._interrupted = True
            logger.debug("TTS: Received interruption/cancel frame, halting audio playback.")
            await self.push_frame(frame, direction)

        elif isinstance(frame, TextFrame):
            text = frame.text.strip()
            if not text:
                await self.push_frame(frame, direction)
                return

            self._interrupted = False
            logger.info("TTS synthesizing text: '%s'", text)
            start_tts = time.perf_counter()

            await self.push_frame(TTSStartedFrame(), direction)

            try:
                result = self.tts.synthesize(text)
                tts_time = (time.perf_counter() - start_tts) * 1000.0
                logger.info(
                    "TTS synthesized in %.1fms (dur: %.2fs, RTF: %.3f)",
                    tts_time,
                    result.duration_seconds,
                    result.rtf,
                )

                if result.samples is not None:
                    # Stream audio in 20ms PCM16 chunks
                    pcm16 = (np.clip(result.samples, -1.0, 1.0) * 32767.0).astype(np.int16)
                    raw_bytes = pcm16.tobytes()
                    bytes_per_chunk = self.chunk_size_samples * 2  # 16-bit = 2 bytes/sample

                    for i in range(0, len(raw_bytes), bytes_per_chunk):
                        if self._interrupted:
                            logger.info("TTS playback interrupted by user speech.")
                            break
                        chunk = raw_bytes[i : i + bytes_per_chunk]
                        await self.push_frame(
                            TTSAudioRawFrame(
                                audio=chunk,
                                sample_rate=self.sample_rate,
                                num_channels=1,
                            ),
                            direction,
                        )

            except Exception as e:
                logger.error("TTS synthesis error: %s", str(e))

            await self.push_frame(TTSStoppedFrame(), direction)

        else:
            await self.push_frame(frame, direction)
