from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes import (
    calls_router,
    contacts_router,
    handoff_router,
    knowledge_router,
    messages_router,
    reminders_router,
    status_router,
    telegram_router,
    telephony_router,
)
from packages.db.session import init_db
from packages.schemas.common import StandardErrorResponse
from packages.schemas.health import HealthResponse
from packages.shared.config import get_settings
from packages.shared.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger("apps.api.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown routines."""
    setup_logging(settings.log_level)
    logger.info(
        "Starting %s v%s in %s mode",
        settings.app_name,
        settings.version,
        settings.environment,
    )

    # Initialize database schemas
    try:
        await init_db()
    except Exception as e:
        logger.warning("Database schema init deferred or database unreachable: %s", e)

    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Personal AI Call Agent REST API with Telephony & Memory Endpoints",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Subsystem Routers
app.include_router(calls_router)
app.include_router(handoff_router)
app.include_router(messages_router)
app.include_router(contacts_router)
app.include_router(knowledge_router)
app.include_router(reminders_router)
app.include_router(status_router)
app.include_router(telegram_router)
app.include_router(telephony_router)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Standardized top-level unhandled exception response."""
    logger.error(
        "Unhandled API error on %s %s: %s", request.method, request.url.path, exc, exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=StandardErrorResponse(
            error="Internal Server Error",
            detail=str(exc)
            if settings.environment == "development"
            else "An unexpected error occurred.",
        ).model_dump(),
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    """System health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.version,
        environment=settings.environment,
    )


@app.get("/", tags=["Root"])
async def get_root() -> dict[str, str]:
    """Root entry point."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
    }
