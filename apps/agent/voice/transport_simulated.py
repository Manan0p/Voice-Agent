from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class SimulatedAudioInputProcessor(FrameProcessor):
    """Feeds synthetic or recorded audio frames into the pipeline for testing."""

    def __init__(self, sample_rate: int = 16000) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.frames_to_feed: list[Frame] = []

    def queue_turn(self, pcm_bytes: bytes) -> None:
        """Queue a user turn with start and stop speaking frames."""
        self.frames_to_feed.append(UserStartedSpeakingFrame())
        chunk_size = int(self.sample_rate * 0.02 * 2)  # 640 bytes for 20ms @ 16kHz
        for i in range(0, len(pcm_bytes), chunk_size):
            chunk = pcm_bytes[i : i + chunk_size]
            self.frames_to_feed.append(
                AudioRawFrame(
                    audio=chunk,
                    sample_rate=self.sample_rate,
                    num_channels=1,
                )
            )
        self.frames_to_feed.append(UserStoppedSpeakingFrame())


class SimulatedAudioOutputProcessor(FrameProcessor):
    """Captures all frames emitted by the pipeline for test assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.received_frames: list[Frame] = []
        self.synthesized_audio_bytes = bytearray()
        self.transcribed_texts: list[str] = []
        self.agent_responses: list[str] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        self.received_frames.append(frame)

        if isinstance(frame, AudioRawFrame):
            self.synthesized_audio_bytes.extend(frame.audio)
        elif isinstance(frame, TranscriptionFrame):
            self.transcribed_texts.append(frame.text)
        elif isinstance(frame, TextFrame):
            self.agent_responses.append(frame.text)

        await self.push_frame(frame, direction)
