import time

import numpy as np
from pipecat.frames.frames import (
    AudioRawFrame,
    CancelFrame,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from apps.agent.stt.base import STTProvider
from apps.agent.stt.factory import get_stt_provider
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.voice.stt_service")


class FasterWhisperSTTService(FrameProcessor):
    """Pipecat FrameProcessor wrapping FasterWhisperProvider with audio buffering on speech."""

    def __init__(
        self,
        stt_provider: STTProvider | None = None,
        sample_rate: int = 16000,
    ) -> None:
        super().__init__()
        self.stt = stt_provider or get_stt_provider()
        self.sample_rate = sample_rate
        self._audio_buffer = bytearray()
        self._is_user_speaking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process incoming Pipecat frames."""
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            self._is_user_speaking = True
            self._audio_buffer.clear()
            logger.debug("VAD: User started speaking, cleared audio buffer.")
            await self.push_frame(frame, direction)

        elif isinstance(frame, (AudioRawFrame, InputAudioRawFrame)):
            # Accumulate audio frames during speech
            self._audio_buffer.extend(frame.audio)
            await self.push_frame(frame, direction)

        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._is_user_speaking = False
            logger.debug(
                "VAD: User stopped speaking. Audio buffer: %d bytes",
                len(self._audio_buffer),
            )

            if len(self._audio_buffer) >= (self.sample_rate * 2 * 0.3):  # Min 0.3s audio
                # Convert raw PCM bytes to float32 ndarray for whisper
                pcm_data = (
                    np.frombuffer(self._audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
                )

                start_stt = time.perf_counter()
                try:
                    result = self.stt.transcribe(pcm_data)
                    latency = (time.perf_counter() - start_stt) * 1000.0
                    text = result.text.strip()
                    if text:
                        print(f"👤 [You]: {text}", flush=True)
                        logger.info("STT Transcribed: '%s' (latency: %.1fms)", text, latency)
                        await self.push_frame(
                            TranscriptionFrame(
                                text=text,
                                user_id="caller",
                                timestamp=time.time(),
                                language=result.language,
                            ),
                            direction,
                        )

                except Exception as e:
                    logger.error("STT transcription error: %s", str(e))

            self._audio_buffer.clear()
            await self.push_frame(frame, direction)

        elif isinstance(frame, (InterruptionFrame, CancelFrame)):
            self._audio_buffer.clear()
            self._is_user_speaking = False
            await self.push_frame(frame, direction)

        else:
            await self.push_frame(frame, direction)
