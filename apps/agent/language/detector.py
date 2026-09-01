import re
from dataclasses import asdict, dataclass
from typing import Literal

from apps.agent.language.lexicon import HINDI_ROMANIZED_WORDS


@dataclass
class LanguageAnalysisResult:
    """Structured result of linguistic analysis for Hindi, English, and Hinglish."""

    english_ratio: float
    hindi_ratio: float
    dominant_language: Literal["english", "hindi", "mixed"]
    style: Literal["pure_english", "pure_hindi", "hinglish"]
    detected_script: Literal["latin", "devanagari", "mixed"] = "latin"
    total_tokens: int = 0

    def to_dict(self) -> dict[str, float | str | int]:
        """Serialize analysis result to standard dictionary format."""
        return asdict(self)


class LanguageDetector:
    """Detects and scores language composition across English, Hindi, and Hinglish code-switching."""

    DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")
    WORD_PATTERN = re.compile(r"[a-zA-Z\u0900-\u097F]+(?:'[a-zA-Z]+)?")

    HINDI_SUFFIXES = (
        "unga",
        "ungi",
        "enge",
        "iye",
        "iyega",
        "kar",
        "gaya",
        "gayi",
        "wale",
        "wali",
        "wala",
    )

    def analyze(self, text: str) -> LanguageAnalysisResult:
        """Analyze input text and compute linguistic ratios and conversational style."""
        clean_text = text.strip()
        if not clean_text:
            return LanguageAnalysisResult(
                english_ratio=1.0,
                hindi_ratio=0.0,
                dominant_language="english",
                style="pure_english",
                detected_script="latin",
                total_tokens=0,
            )

        # Check for Devanagari characters
        devanagari_chars = len(self.DEVANAGARI_PATTERN.findall(clean_text))
        total_alpha_chars = len([c for c in clean_text if c.isalpha() or "\u0900" <= c <= "\u097f"])

        has_devanagari = devanagari_chars > 0
        is_predominantly_devanagari = (
            total_alpha_chars > 0 and (devanagari_chars / total_alpha_chars) > 0.5
        )

        tokens = self.WORD_PATTERN.findall(clean_text.lower())
        total_tokens = len(tokens)

        if total_tokens == 0:
            return LanguageAnalysisResult(
                english_ratio=1.0,
                hindi_ratio=0.0,
                dominant_language="english",
                style="pure_english",
                detected_script="latin",
                total_tokens=0,
            )

        hindi_tokens_count = 0.0
        english_tokens_count = 0.0

        for token in tokens:
            if self.DEVANAGARI_PATTERN.search(token):
                hindi_tokens_count += 1.0
            elif token in HINDI_ROMANIZED_WORDS or token.endswith(self.HINDI_SUFFIXES):
                hindi_tokens_count += 1.0
            else:
                # Latin token not matching Hindi lexicon is English
                english_tokens_count += 1.0

        if hindi_tokens_count == 0.0:
            hindi_ratio = 0.0
            english_ratio = 1.0
        elif english_tokens_count == 0.0:
            hindi_ratio = 1.0
            english_ratio = 0.0
        else:
            raw_hindi = hindi_tokens_count / float(total_tokens)
            hindi_ratio = round(raw_hindi, 2)
            english_ratio = round(1.0 - hindi_ratio, 2)

        # Classify dominant language
        if hindi_ratio >= 0.60:
            dominant_language: Literal["english", "hindi", "mixed"] = "hindi"
        elif english_ratio >= 0.60:
            dominant_language = "english"
        else:
            dominant_language = "mixed"

        # Classify style
        if is_predominantly_devanagari or (hindi_ratio >= 0.85 and english_tokens_count == 0):
            style: Literal["pure_english", "pure_hindi", "hinglish"] = "pure_hindi"
        elif english_ratio >= 0.85 or hindi_tokens_count == 0:
            style = "pure_english"
        else:
            style = "hinglish"

        # Script classification
        if has_devanagari and not is_predominantly_devanagari:
            detected_script: Literal["latin", "devanagari", "mixed"] = "mixed"
        elif has_devanagari:
            detected_script = "devanagari"
        else:
            detected_script = "latin"

        return LanguageAnalysisResult(
            english_ratio=english_ratio,
            hindi_ratio=hindi_ratio,
            dominant_language=dominant_language,
            style=style,
            detected_script=detected_script,
            total_tokens=total_tokens,
        )
