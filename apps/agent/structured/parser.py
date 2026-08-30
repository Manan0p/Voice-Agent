import json
import re

from pydantic import BaseModel, ValidationError

from packages.shared.logging import get_logger

logger = get_logger("apps.agent.structured.parser")


def extract_json_string(text: str) -> str:
    """Extract first JSON block or object from markdown or conversational text."""
    # 1. Check for markdown json code blocks ```json { ... } ```
    markdown_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if markdown_match:
        candidate = markdown_match.group(1).strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate

    # 2. Check for outermost curly braces { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()

    return text.strip()


def parse_structured[T: BaseModel](text: str, schema_cls: type[T]) -> T:
    """Parse raw LLM response text into a validated Pydantic model instance."""
    clean_text = extract_json_string(text)
    try:
        data = json.loads(clean_text)
        return schema_cls.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning("Failed to parse structured response (%s): %s", str(e), clean_text)
        raise ValueError(
            f"Could not parse structured output as {schema_cls.__name__}: {str(e)}"
        ) from e
