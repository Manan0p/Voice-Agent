from typing import Any

from pydantic import BaseModel, Field

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolResult


class GetContactInput(BaseModel):
    """Input parameters for looking up a contact."""

    query: str = Field(description="Name, relationship, or phone number of the contact to look up.")


class GetContactTool(BaseTool):
    """Tool to search and retrieve contact details from the user's address book."""

    name = "get_contact"
    description = "Look up a contact's details, phone number, relationship, and organization by name or number."
    permission_level = PermissionLevel.READ_ONLY
    args_schema = GetContactInput

    CONTACTS_DB: list[dict[str, Any]] = [
        {"name": "Manan", "phone": "+91-9876543210", "relationship": "self", "org": "Owner"},
        {"name": "Mummy", "phone": "+91-9811122233", "relationship": "family", "org": "Family"},
        {"name": "Papa", "phone": "+91-9822233344", "relationship": "family", "org": "Family"},
        {"name": "Rahul", "phone": "+91-9833344455", "relationship": "friend", "org": "Personal"},
        {
            "name": "Sneha",
            "phone": "+91-9844455566",
            "relationship": "colleague",
            "org": "TechCorp",
        },
        {
            "name": "Priya",
            "phone": "+91-9988776652",
            "relationship": "recruiter",
            "org": "Microsoft",
        },
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Search contacts by query string."""
        query = kwargs.get("query", "").strip().lower()
        if not query:
            return ToolResult(success=False, error="Query parameter is required")

        matches = []
        for contact in self.CONTACTS_DB:
            if (
                query in contact["name"].lower()
                or query in contact["phone"]
                or query in contact["relationship"].lower()
                or query in contact.get("org", "").lower()
            ):
                matches.append(contact)

        if matches:
            return ToolResult(
                success=True,
                data={"found": True, "count": len(matches), "contacts": matches},
            )

        return ToolResult(
            success=True,
            data={
                "found": False,
                "count": 0,
                "contacts": [],
                "message": f"No contact found matching '{query}'",
            },
        )


class GetCallerHistoryInput(BaseModel):
    """Input parameters for retrieving caller history."""

    caller_id: str | None = Field(
        default=None, description="Optional phone number of the caller to inspect."
    )


class GetCallerHistoryTool(BaseTool):
    """Tool to inspect past call summaries, past messages, and relationship notes for a caller."""

    name = "get_caller_history"
    description = "Retrieve past call history, previous messages, and notes for the active caller."
    permission_level = PermissionLevel.READ_ONLY
    args_schema = GetCallerHistoryInput

    CALL_HISTORY_DB: dict[str, list[dict[str, Any]]] = {
        "+91-9811122233": [
            {
                "date": "2026-08-28",
                "summary": "Mummy called to check on dinner and flight tickets.",
                "duration_sec": 140,
            },
            {
                "date": "2026-08-30",
                "summary": "Mummy asked if Diwali festival dates are confirmed.",
                "duration_sec": 95,
            },
        ],
        "+91-9833344455": [
            {
                "date": "2026-08-25",
                "summary": "Rahul called about Goa trip planning and flight booking.",
                "duration_sec": 210,
            },
        ],
        "+91-9844455566": [
            {
                "date": "2026-08-29",
                "summary": "Sneha called regarding pull request code review on GitHub.",
                "duration_sec": 180,
            },
        ],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Retrieve interaction history for caller."""
        caller_id = kwargs.get("caller_id") or kwargs.get("_caller_id") or "unknown"
        history = self.CALL_HISTORY_DB.get(caller_id, [])

        return ToolResult(
            success=True,
            data={
                "caller_id": caller_id,
                "total_past_calls": len(history),
                "history": history,
            },
        )
