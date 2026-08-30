from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Personal AI Call Agent REST API",
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
