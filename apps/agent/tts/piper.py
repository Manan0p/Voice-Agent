from typing import Any

from apps.agent.tts.base import TTSProvider, TTSResult
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.tts.piper")


class PiperTTSProvider(TTSProvider):
    """Fallback Piper TTS provider."""

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path
        logger.info("Piper TTS provider initialized (fallback mode)")

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs: Any,
    ) -> TTSResult:
        """Synthesize audio using Piper or fallback."""
        # Baseline fallback implementation
        raise NotImplementedError("Piper provider requires piper binary/onnx model configured.")
