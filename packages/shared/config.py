from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application global settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "Personal AI Call Agent"
    version: str = "0.1.0"
    environment: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_caller"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "personal_caller"

    # AI Models & LLM Providers
    llm_provider: Literal["gemini", "ollama", "mock"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"
    ollama_base_url: str = "http://localhost:11434"
    qwen_model_name: str = "qwen2.5:7b-instruct"

    # STT & Audio Settings (Phase 2)
    stt_provider: Literal["whisper", "mock"] = "whisper"
    whisper_model_size: str = "base"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"

    # TTS Settings (Phase 3)
    tts_provider: Literal["kokoro", "piper", "mock"] = "kokoro"
    kokoro_voice: str = "af_bella"
    kokoro_speed: float = 1.0
    kokoro_model_dir: str = "models/kokoro"

    # Realtime Voice Pipeline & VAD (Phase 4)
    vad_start_secs: float = 0.2
    vad_stop_secs: float = 0.6
    audio_input_sample_rate: int = 16000
    audio_output_sample_rate: int = 24000


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
