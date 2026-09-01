from dataclasses import dataclass
from typing import Literal

from apps.agent.language.detector import LanguageAnalysisResult, LanguageDetector


@dataclass
class ConversationalLanguageState:
    """Multi-turn aggregated linguistic state of the caller."""

    current_turn_analysis: LanguageAnalysisResult
    rolling_english_ratio: float
    rolling_hindi_ratio: float
    dominant_conversation_language: Literal["english", "hindi", "mixed"]
    conversation_style: Literal["pure_english", "pure_hindi", "hinglish"]
    turn_count: int
    has_language_shifted: bool = False
    shift_details: str | None = None


class LanguageTracker:
    """Tracks linguistic progression and code-switching momentum across conversational turns."""

    def __init__(self, detector: LanguageDetector | None = None, history_window: int = 5) -> None:
        self.detector = detector or LanguageDetector()
        self.history_window = history_window
        self.turn_history: list[LanguageAnalysisResult] = []

    def update(self, user_utterance: str) -> ConversationalLanguageState:
        """Analyze a new turn and update rolling language state and shift detection."""
        analysis = self.detector.analyze(user_utterance)
        self.turn_history.append(analysis)

        recent_turns = self.turn_history[-self.history_window :]
        turn_count = len(self.turn_history)

        # Compute weighted rolling average (recent turns weighted slightly higher)
        weights = [1.0 + (0.2 * i) for i in range(len(recent_turns))]
        total_weight = sum(weights)

        weighted_hindi = (
            sum(t.hindi_ratio * w for t, w in zip(recent_turns, weights, strict=False))
            / total_weight
        )
        rolling_hindi_ratio = round(weighted_hindi, 2)
        rolling_english_ratio = round(1.0 - rolling_hindi_ratio, 2)

        # Dominant conversation language
        if rolling_hindi_ratio >= 0.60:
            dom_lang: Literal["english", "hindi", "mixed"] = "hindi"
        elif rolling_english_ratio >= 0.60:
            dom_lang = "english"
        else:
            dom_lang = "mixed"

        # Conversation style
        if rolling_hindi_ratio >= 0.85:
            conv_style: Literal["pure_english", "pure_hindi", "hinglish"] = "pure_hindi"
        elif rolling_english_ratio >= 0.85:
            conv_style = "pure_english"
        else:
            conv_style = "hinglish"

        # Detect language shift from previous turns
        has_shifted = False
        shift_details = None

        if turn_count >= 2:
            prev_analysis = self.turn_history[-2]
            if prev_analysis.style != analysis.style:
                has_shifted = True
                shift_details = f"Caller switched from {prev_analysis.style} to {analysis.style} in current turn."

        return ConversationalLanguageState(
            current_turn_analysis=analysis,
            rolling_english_ratio=rolling_english_ratio,
            rolling_hindi_ratio=rolling_hindi_ratio,
            dominant_conversation_language=dom_lang,
            conversation_style=conv_style,
            turn_count=turn_count,
            has_language_shifted=has_shifted,
            shift_details=shift_details,
        )

    def reset(self) -> None:
        """Clear conversation turn history."""
        self.turn_history.clear()
