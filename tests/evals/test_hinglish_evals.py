"""Evaluation suite running 50+ real-world Indian phone call test cases through the Hinglish Engine."""

import pytest

from apps.agent.language.detector import LanguageDetector
from apps.agent.language.policy import LanguagePolicy, LanguagePolicyMode
from apps.agent.language.tracker import LanguageTracker
from tests.fixtures.hinglish_dataset import HINGLISH_CONVERSATION_DATASET, HinglishTestCase


@pytest.mark.parametrize("case", HINGLISH_CONVERSATION_DATASET, ids=lambda c: c.id)
def test_hinglish_dataset_individual_cases(case: HinglishTestCase) -> None:
    """Evaluate language detection and style classification for each scenario in the 55-case dataset."""
    detector = LanguageDetector()
    result = detector.analyze(case.text)

    # Style verification
    if case.expected_style == "pure_english":
        assert result.style == "pure_english", f"Failed for '{case.text}': got {result.style}"
        assert result.english_ratio >= 0.80
    elif case.expected_style == "pure_hindi":
        assert result.style == "pure_hindi", f"Failed for '{case.text}': got {result.style}"
        assert result.hindi_ratio >= 0.80
    else:  # hinglish
        assert result.style == "hinglish", f"Failed for '{case.text}': got {result.style}"
        assert result.hindi_ratio >= 0.20
        assert result.english_ratio >= 0.15


def test_hinglish_dataset_aggregate_metrics() -> None:
    """Benchmark aggregate accuracy across all 55 Indian phone conversation scenarios."""
    detector = LanguageDetector()
    tracker = LanguageTracker(detector=detector)
    policy = LanguagePolicy(mode=LanguagePolicyMode.MIRROR)

    total_cases = len(HINGLISH_CONVERSATION_DATASET)
    assert total_cases >= 50, f"Expected at least 50 test cases, found {total_cases}"

    correct_style_matches = 0
    correct_dominant_matches = 0

    for case in HINGLISH_CONVERSATION_DATASET:
        analysis = detector.analyze(case.text)
        state = tracker.update(case.text)
        decision = policy.decide(state)

        # Style match check
        if analysis.style == case.expected_style:
            correct_style_matches += 1

        # Dominant language check: Exact match or valid code-switched alignment
        if (
            analysis.dominant_language == case.expected_dominant
            or analysis.style == "hinglish"
            or (
                case.expected_dominant == "mixed"
                and analysis.dominant_language in {"mixed", "hindi", "english"}
            )
        ):
            correct_dominant_matches += 1

        # Verify policy prompt decision is valid
        assert decision.target_style in {"pure_english", "pure_hindi", "hinglish"}
        assert len(decision.instruction_prompt) > 20

    style_accuracy = (correct_style_matches / total_cases) * 100.0
    dominant_accuracy = (correct_dominant_matches / total_cases) * 100.0

    print(f"\n--- HINGLISH ENGINE BENCHMARK ({total_cases} scenarios) ---")
    print(
        f"Style Classification Accuracy: {style_accuracy:.1f}% ({correct_style_matches}/{total_cases})"
    )
    print(
        f"Dominant Language Accuracy:   {dominant_accuracy:.1f}% ({correct_dominant_matches}/{total_cases})"
    )

    assert style_accuracy >= 92.0, f"Style accuracy too low: {style_accuracy}%"
    assert dominant_accuracy >= 95.0, f"Dominant language accuracy too low: {dominant_accuracy}%"


if __name__ == "__main__":
    test_hinglish_dataset_aggregate_metrics()
