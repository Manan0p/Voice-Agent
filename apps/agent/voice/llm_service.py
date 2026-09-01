import asyncio
import time

from pipecat.frames.frames import (
    CancelFrame,
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from apps.agent.engine import AgentEngine
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.voice.llm_service")


class AgentEngineLLMService(FrameProcessor):
    """Pipecat FrameProcessor connecting conversational turns to AgentEngine with single-turn locking."""

    def __init__(self, engine: AgentEngine | None = None) -> None:
        super().__init__()
        self.engine = engine or AgentEngine()
        self._interrupted = False
        self._is_generating = False
        self._lock = asyncio.Lock()

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process frames and trigger agent reasoning on user transcription."""
        await super().process_frame(frame, direction)

        if isinstance(frame, (InterruptionFrame, CancelFrame)):
            self._interrupted = True
            await self.push_frame(frame, direction)

        elif isinstance(frame, (TranscriptionFrame, TextFrame)):
            text = frame.text.strip()
            if not text:
                await self.push_frame(frame, direction)
                return

            # Avoid concurrent overlapping LLM generations from rapid speech triggers
            async with self._lock:
                self._interrupted = False
                self._is_generating = True
                logger.info("LLM turn started for input: '%s'", text)
                start_llm = time.perf_counter()

                await self.push_frame(LLMFullResponseStartFrame(), direction)

                try:
                    # Use engine.step to handle tools, conversation history, and context
                    result = await self.engine.step(text)
                    llm_time = (time.perf_counter() - start_llm) * 1000.0
                    logger.info(
                        "LLM response generated in %.1fms: '%s'",
                        llm_time,
                        result.response_text,
                    )

                    if not self._interrupted and result.response_text:
                        print(f"🤖 [Agent]: {result.response_text}", flush=True)
                        await self.push_frame(TextFrame(text=result.response_text), direction)

                except Exception as e:
                    logger.error("LLM reasoning error: %s", str(e))
                    await self.push_frame(
                        TextFrame(text="I apologize, could you please repeat that?"),
                        direction,
                    )
                finally:
                    self._is_generating = False

                await self.push_frame(LLMFullResponseEndFrame(), direction)

        else:
            await self.push_frame(frame, direction)
