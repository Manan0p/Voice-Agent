from typing import Any

from pydantic import BaseModel, Field

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolResult


class SearchKnowledgeInput(BaseModel):
    """Input parameters for searching personal knowledge base."""

    query: str = Field(
        description="Search terms for finding owner availability, project details, or FAQ facts."
    )
    category: str | None = Field(
        default=None,
        description="Optional filter category (e.g., 'calendar', 'project', 'preferences').",
    )


class SearchKnowledgeTool(BaseTool):
    """Tool to search the owner's allowlisted personal knowledge base and schedule preferences."""

    name = "search_knowledge"
    description = "Search owner's schedule preferences, meeting availability, project facts, and permissible public information."
    permission_level = PermissionLevel.READ_ONLY
    args_schema = SearchKnowledgeInput

    KNOWLEDGE_BASE: list[dict[str, Any]] = [
        {
            "category": "calendar",
            "topic": "meeting_availability",
            "content": "Manan is available for technical discussions and interviews on weekdays between 2 PM and 6 PM IST. Prefers Google Meet or Zoom.",
        },
        {
            "category": "calendar",
            "topic": "morning_focus_time",
            "content": "Mornings (9 AM to 1 PM IST) are reserved for deep coding and focus time. Routine calls should be scheduled for the afternoon.",
        },
        {
            "category": "project",
            "topic": "current_work",
            "content": "Manan is actively building a Real-Time Personal AI Voice Agent with Pipecat, Faster-Whisper, Kokoro TTS, and local telephony.",
        },
        {
            "category": "preferences",
            "topic": "deliveries",
            "content": "Delivery partners can leave packages with the security guard at the apartment reception gate if Manan is unavailable.",
        },
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Search knowledge items matching query keywords."""
        query = kwargs.get("query", "").strip().lower()
        category = kwargs.get("category")

        if not query:
            return ToolResult(success=False, error="Search query cannot be empty")

        words = [w for w in query.replace("_", " ").split() if len(w) > 2]
        matches = []
        for item in self.KNOWLEDGE_BASE:
            if category and item["category"] != category:
                continue

            topic_text = item["topic"].lower().replace("_", " ")
            content_text = item["content"].lower()

            if (
                query in topic_text
                or query in content_text
                or any(w in topic_text or w in content_text for w in words)
            ):
                matches.append(item)

        return ToolResult(
            success=True,
            data={
                "query": query,
                "found_count": len(matches),
                "results": matches,
            },
        )
