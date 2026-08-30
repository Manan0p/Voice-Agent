import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from apps.agent.llm.base import LLMMessage, LLMProvider, LLMResponse, Role, ToolCall
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.llm.gemini")


class GeminiProvider(LLMProvider):
    """Google Gemini LLM Provider using direct async REST API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _convert_messages_to_gemini(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert internal LLMMessages to Gemini contents structure."""
        contents: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                # System prompt is handled separately in systemInstruction
                continue

            role = "user" if msg.role == Role.USER else "model"
            parts: list[dict[str, Any]] = []

            if msg.content:
                parts.append({"text": msg.content})

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    parts.append(
                        {
                            "functionCall": {
                                "name": tc.name,
                                "args": tc.arguments,
                            }
                        }
                    )

            if msg.role == Role.TOOL:
                parts.append(
                    {
                        "functionResponse": {
                            "name": msg.name or "tool_result",
                            "response": {"result": msg.content},
                        }
                    }
                )

            if parts:
                contents.append({"role": role, "parts": parts})

        return contents

    def _convert_tools_to_gemini(
        self, tools: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]] | None:
        """Convert standard tool schemas to Gemini function declarations."""
        if not tools:
            return None

        declarations = []
        for tool in tools:
            decl: dict[str, Any] = {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
            }
            if "parameters" in tool:
                decl["parameters"] = tool["parameters"]
            declarations.append(decl)

        return [{"functionDeclarations": declarations}]

    async def generate(
        self,
        messages: list[LLMMessage],
        system_instruction: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> LLMResponse:
        """Send chat request to Gemini REST API."""
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please set it in .env or environment variables."
            )

        endpoint = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        contents = self._convert_messages_to_gemini(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        gemini_tools = self._convert_tools_to_gemini(tools)
        if gemini_tools:
            payload["tools"] = gemini_tools

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code != 200:
                    logger.error(
                        "Gemini API error %d: %s",
                        response.status_code,
                        response.text,
                    )
                    response.raise_for_status()

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return LLMResponse(
                        content="",
                        latency_ms=latency_ms,
                        finish_reason="no_candidates",
                    )

                candidate = candidates[0]
                content_parts = candidate.get("content", {}).get("parts", [])
                finish_reason = candidate.get("finishReason", "STOP")

                text_content = ""
                tool_calls: list[ToolCall] = []

                for part in content_parts:
                    if "text" in part:
                        text_content += part["text"]
                    elif "functionCall" in part:
                        fn = part["functionCall"]
                        tool_calls.append(
                            ToolCall(
                                id=f"call_{int(time.time() * 1000)}",
                                name=fn.get("name", ""),
                                arguments=fn.get("args", {}),
                            )
                        )

                usage = data.get("usageMetadata", {})
                return LLMResponse(
                    content=text_content.strip(),
                    tool_calls=tool_calls,
                    finish_reason=finish_reason,
                    latency_ms=latency_ms,
                    prompt_tokens=usage.get("promptTokenCount", 0),
                    completion_tokens=usage.get("candidatesTokenCount", 0),
                )

            except httpx.HTTPStatusError as e:
                logger.error("Gemini HTTP error: %s", str(e))
                raise
            except Exception as e:
                logger.error("Gemini unexpected error: %s", str(e))
                raise

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> AsyncGenerator[str, None]:
        """Stream chunks from Gemini REST API."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        endpoint = (
            f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        )
        contents = self._convert_messages_to_gemini(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str:
                            try:
                                chunk = json.loads(data_str)
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        if "text" in part:
                                            yield part["text"]
                            except json.JSONDecodeError:
                                continue
