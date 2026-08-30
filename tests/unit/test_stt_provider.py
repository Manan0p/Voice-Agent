from apps.agent.stt.base import TranscriptionResult, TranscriptionSegment
from apps.agent.stt.factory import get_stt_provider
from apps.agent.stt.mock import MockSTTProvider
from packages.shared.config import Settings


def test_transcription_result_rtf_calculation() -> None:
    """Verify Real-Time Factor (RTF) calculation."""
    # 2.0s audio transcribed in 500ms (0.5s) -> RTF = 0.25
    result = TranscriptionResult(
        text="Hello world",
        duration=2.0,
        latency_ms=500.0,
        segments=[TranscriptionSegment(id=0, start=0.0, end=2.0, text="Hello world")],
    )
    assert result.rtf == 0.25
    assert result.text == "Hello world"
    assert len(result.segments) == 1


def test_mock_stt_provider() -> None:
    """Verify MockSTTProvider handles transcription calls cleanly."""
    mock = MockSTTProvider(
        default_text="Bhai kal meeting fix karni hai.",
        default_language="hi",
    )
    result = mock.transcribe("fake_audio.wav")
    assert result.text == "Bhai kal meeting fix karni hai."
    assert result.language == "hi"
    assert result.duration > 0.0
    assert result.latency_ms > 0.0
    assert len(mock.transcribe_calls) == 1


def test_stt_factory_mock() -> None:
    """Verify factory returns MockSTTProvider when configured."""
    settings = Settings(stt_provider="mock")
    provider = get_stt_provider(settings)
    assert isinstance(provider, MockSTTProvider)
