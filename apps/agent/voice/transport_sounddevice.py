import queue
import threading
import time
from typing import Any

import sounddevice as sd
from pipecat.frames.frames import (
    AudioRawFrame,
    CancelFrame,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    TTSAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from packages.shared.logging import get_logger

logger = get_logger("apps.agent.voice.transport_sounddevice")


class SoundDeviceInputProcessor(FrameProcessor):
    """Captures microphone audio (16kHz mono) and pushes InputAudioRawFrames."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        block_size: int = 640,  # 40ms @ 16kHz
    ) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._stream: sd.RawInputStream | None = None
        self._running = False

    def start(self) -> None:
        """Start microphone audio capture stream."""
        if self._running:
            return

        def _callback(indata: bytes, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
            if status:
                logger.warning("SoundDevice input status: %s", status)
            self._queue.put(bytes(indata))

        try:
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=self.block_size,
                callback=_callback,
            )
            self._stream.start()
            self._running = True
            logger.info("Microphone stream active (%dHz, mono).", self.sample_rate)
        except Exception as e:
            logger.error("Failed to open microphone stream: %s", str(e))
            raise

    def stop(self) -> None:
        """Stop microphone capture stream."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def get_chunk(self) -> bytes:
        """Read one raw audio chunk from microphone queue."""
        return self._queue.get()


class SoundDeviceOutputProcessor(FrameProcessor):
    """Plays synthesized audio frames through PC speakers with echo suppression tracking."""

    def __init__(
        self,
        sample_rate: int = 24000,
        channels: int = 1,
    ) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self._queue: queue.Queue[bytes | None] = queue.Queue()
        self._stream: sd.RawOutputStream | None = None
        self._running = False
        self._playback_thread: threading.Thread | None = None
        self._last_playback_time: float = 0.0

    @property
    def is_playing(self) -> bool:
        """Returns True if the speaker is currently outputting sound or within the reverb tail."""
        if not self._queue.empty():
            return True
        # Allow 350ms acoustic reverb guard tail after playback ends
        return (time.time() - self._last_playback_time) < 0.35

    def start(self) -> None:
        """Start speaker playback worker."""
        if self._running:
            return

        try:
            self._stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
            )
            self._stream.start()
            self._running = True

            def _playback_worker() -> None:
                while self._running:
                    try:
                        chunk = self._queue.get(timeout=0.05)
                        if chunk is None:
                            continue
                        if self._stream and self._running:
                            self._last_playback_time = time.time()
                            self._stream.write(chunk)
                            self._last_playback_time = time.time()
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error("Speaker write error: %s", str(e))

            self._playback_thread = threading.Thread(target=_playback_worker, daemon=True)
            self._playback_thread.start()
            logger.info("Speaker output stream active (%dHz).", self.sample_rate)
        except Exception as e:
            logger.error("Failed to start speaker stream: %s", str(e))
            raise

    def stop(self) -> None:
        """Stop speaker stream."""
        self._running = False
        self.flush()
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def flush(self) -> None:
        """Clear playback queue immediately on interruption."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._last_playback_time = 0.0

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Queue audio frames for speaker playback."""
        await super().process_frame(frame, direction)

        if isinstance(frame, (InterruptionFrame, CancelFrame)):
            self.flush()
            logger.info("Interruption received: Speaker playback halted.")
            await self.push_frame(frame, direction)

        elif isinstance(frame, (AudioRawFrame, TTSAudioRawFrame, InputAudioRawFrame)):
            if not self._running:
                self.start()
            self._last_playback_time = time.time()
            self._queue.put(frame.audio)
            await self.push_frame(frame, direction)

        else:
            await self.push_frame(frame, direction)
