from apps.agent.language.detector import LanguageDetector
from apps.agent.language.policy import LanguagePolicy, LanguagePolicyMode
from apps.agent.language.tracker import LanguageTracker


def test_language_detector_pure_english() -> None:
    """Verify detector correctly identifies English text with high English ratio."""
    detector = LanguageDetector()
    res = detector.analyze("Hello, this is John calling regarding the project update and timeline.")
    assert res.style == "pure_english"
    assert res.dominant_language == "english"
    assert res.english_ratio >= 0.85
    assert res.hindi_ratio <= 0.15
    assert res.detected_script == "latin"


def test_language_detector_pure_devanagari_hindi() -> None:
    """Verify detector identifies Devanagari Hindi text and script."""
    detector = LanguageDetector()
    res = detector.analyze("नमस्ते, क्या मनन जी उपलब्ध हैं? मुझे उनसे बात करनी थी।")
    assert res.style == "pure_hindi"
    assert res.dominant_language == "hindi"
    assert res.hindi_ratio >= 0.85
    assert res.detected_script == "devanagari"


def test_language_detector_hinglish_code_switching() -> None:
    """Verify detector identifies code-switched Hinglish with mixed ratios."""
    detector = LanguageDetector()
    res = detector.analyze(
        "Bhai interview reschedule karna hai. Kal 3 PM pe zoom call theek rahega?"
    )
    assert res.style == "hinglish"
    assert res.dominant_language in {"mixed", "hindi"}
    assert 0.20 <= res.english_ratio <= 0.80
    assert 0.20 <= res.hindi_ratio <= 0.80


def test_language_tracker_momentum_and_shift_detection() -> None:
    """Verify tracker computes rolling averages and detects language shifts between turns."""
    tracker = LanguageTracker()

    # Turn 1: English
    t1 = tracker.update("Hello, I would like to speak with Manan regarding an urgent matter.")
    assert t1.dominant_conversation_language == "english"
    assert t1.has_language_shifted is False

    # Turn 2: Switch to Hinglish
    t2 = tracker.update("Arre bhai, actually meeting ka time change ho gaya hai.")
    assert t2.has_language_shifted is True
    assert "Caller switched" in (t2.shift_details or "")

    # Turn 3: Continue in Hinglish
    t3 = tracker.update("Kal morning 11 baje connect karein kya?")
    assert t3.turn_count == 3
    assert t3.conversation_style == "hinglish"


def test_language_policy_mirroring() -> None:
    """Verify LanguagePolicy generates appropriate system directives in MIRROR mode."""
    detector = LanguageDetector()
    tracker = LanguageTracker(detector=detector)
    policy = LanguagePolicy(mode=LanguagePolicyMode.MIRROR)

    # Test English mirror
    state_en = tracker.update("Can you please ask him to review the document today?")
    decision_en = policy.decide(state_en)
    assert decision_en.target_style == "pure_english"
    assert "clear, professional English" in decision_en.instruction_prompt

    # Test Hinglish mirror
    state_hi = tracker.update("Haan bilkul, unhe bol dena ki main evening mein call karunga.")
    decision_hi = policy.decide(state_hi)
    assert decision_hi.target_style == "hinglish"
    assert "Mirror their exact code-switching" in decision_hi.instruction_prompt


def test_language_policy_force_modes() -> None:
    """Verify force modes override caller language."""
    tracker = LanguageTracker()
    state = tracker.update("नमस्ते, मैं बाद में बात करूँगा।")

    policy_force_en = LanguagePolicy(mode=LanguagePolicyMode.FORCE_ENGLISH)
    decision = policy_force_en.decide(state)
    assert decision.target_style == "pure_english"
    assert "STRICTLY in natural, polite English" in decision.instruction_prompt

    policy_force_hi = LanguagePolicy(mode=LanguagePolicyMode.FORCE_HINDI)
    decision_hi = policy_force_hi.decide(state)
    assert decision_hi.target_style == "pure_hindi"
    assert "polite, natural Hindi" in decision_hi.instruction_prompt
