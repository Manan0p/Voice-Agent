from apps.agent.stt.base import STTProvider
from apps.agent.stt.mock import MockSTTProvider
from apps.agent.stt.whisper import FasterWhisperProvider
from packages.shared.config import Settings, get_settings


def get_stt_provider(settings: Settings | None = None) -> STTProvider:
    """Instantiate and return the configured STT Provider."""
    cfg = settings or get_settings()

    if cfg.stt_provider == "mock":
        return MockSTTProvider()

    return FasterWhisperProvider(
        model_size=cfg.whisper_model_size,
        device=cfg.whisper_device,
        compute_type=cfg.whisper_compute_type,
    )
