from apps.api.routes.calls import router as calls_router
from apps.api.routes.contacts import router as contacts_router
from apps.api.routes.knowledge import router as knowledge_router
from apps.api.routes.messages import router as messages_router
from apps.api.routes.reminders import router as reminders_router
from apps.api.routes.status import router as status_router
from apps.api.routes.telephony import router as telephony_router

__all__ = [
    "calls_router",
    "messages_router",
    "contacts_router",
    "knowledge_router",
    "reminders_router",
    "status_router",
    "telephony_router",
]
