from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from apps.agent.language.tracker import ConversationalLanguageState


class LanguagePolicyMode(StrEnum):
    """Modes governing the agent's linguistic output policy."""

    MIRROR = "mirror"  # Dynamically mirror caller's detected language and code-switching ratio
    FORCE_ENGLISH = "force_english"  # Force English responses regardless of caller
    FORCE_HINDI = "force_hindi"  # Force Hindi responses
    FORCE_HINGLISH = "force_hinglish"  # Force mixed Hinglish responses


@dataclass
class LanguagePolicyDecision:
    """Decision produced by LanguagePolicy for agent prompt injection."""

    target_style: Literal["pure_english", "pure_hindi", "hinglish"]
    target_dominant_language: Literal["english", "hindi", "mixed"]
    instruction_prompt: str
    target_hindi_ratio: float
    target_english_ratio: float


class LanguagePolicy:
    """Determines conversational response language and formats dynamic LLM instructions."""

    def __init__(self, mode: LanguagePolicyMode = LanguagePolicyMode.MIRROR) -> None:
        self.mode = mode

    def decide(self, state: ConversationalLanguageState) -> LanguagePolicyDecision:
        """Determine target language policy based on caller state and policy mode."""
        if self.mode == LanguagePolicyMode.FORCE_ENGLISH:
            target_style = "pure_english"
            target_dom = "english"
            target_hindi = 0.0
            target_english = 1.0
            instruction = (
                "LANGUAGE DIRECTIVE: Respond STRICTLY in natural, polite English. "
                "Do not use Hindi or Hinglish words."
            )

        elif self.mode == LanguagePolicyMode.FORCE_HINDI:
            target_style = "pure_hindi"
            target_dom = "hindi"
            target_hindi = 0.9
            target_english = 0.1
            instruction = (
                "LANGUAGE DIRECTIVE: Respond in polite, natural Hindi (written in Roman script). "
                "Keep English words to an absolute minimum."
            )

        elif self.mode == LanguagePolicyMode.FORCE_HINGLISH:
            target_style = "hinglish"
            target_dom = "mixed"
            target_hindi = 0.5
            target_english = 0.5
            instruction = (
                "LANGUAGE DIRECTIVE: Respond in conversational Indian Hinglish (blend of Hindi and English in Roman script). "
                "Balance Hindi conversational particles (e.g. 'haan', 'bhai', 'theek hai', 'bataiye') with English terms."
            )

        else:  # MIRROR mode
            turn_analysis = state.current_turn_analysis
            target_style = turn_analysis.style
            target_dom = turn_analysis.dominant_language
            target_hindi = state.rolling_hindi_ratio
            target_english = state.rolling_english_ratio

            if target_style == "pure_english":
                instruction = (
                    "LANGUAGE DIRECTIVE: The caller is speaking English. "
                    "Respond strictly in clear, professional English. Do not mix Hindi words."
                )
            elif target_style == "pure_hindi":
                instruction = (
                    "LANGUAGE DIRECTIVE: The caller is speaking Hindi. "
                    "Respond in natural, polite Hindi (in Romanized script for voice synthesis). "
                    "Example: 'Namaste! Main Manan ka AI assistant bol raha hoon. Kaise madad kar sakta hoon?'"
                )
            else:
                instruction = (
                    f"LANGUAGE DIRECTIVE: The caller is speaking Hinglish (approx {int(turn_analysis.hindi_ratio * 100)}% Hindi, "
                    f"{int(turn_analysis.english_ratio * 100)}% English). Mirror their exact code-switching style naturally in Roman script. "
                    "Example: 'Haan bilkul, kal 11 AM meeting ke baare mein note kar liya hai. Aur kuch update dena hai?'"
                )

        return LanguagePolicyDecision(
            target_style=target_style,
            target_dominant_language=target_dom,
            instruction_prompt=instruction,
            target_hindi_ratio=target_hindi,
            target_english_ratio=target_english,
        )
