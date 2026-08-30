from apps.agent.tts.base import TTSProvider
from apps.agent.tts.kokoro import KokoroTTSProvider
from apps.agent.tts.mock import MockTTSProvider
from apps.agent.tts.piper import PiperTTSProvider
from packages.shared.config import Settings, get_settings


def get_tts_provider(settings: Settings | None = None) -> TTSProvider:
    """Instantiate and return the configured TTS Provider."""
    cfg = settings or get_settings()

    if cfg.tts_provider == "mock":
        return MockTTSProvider()
    elif cfg.tts_provider == "piper":
        return PiperTTSProvider()

    # Default: Kokoro
    return KokoroTTSProvider(
        default_voice=cfg.kokoro_voice,
        model_dir=cfg.kokoro_model_dir,
    )
