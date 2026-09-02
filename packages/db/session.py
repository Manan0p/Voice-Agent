import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.db.base import Base
from packages.shared.logging import get_logger

logger = get_logger("packages.db.session")


def get_database_url() -> str:
    """Retrieve async database connection URL from environment or default to asyncpg."""
    url = os.getenv("DATABASE_URL")
    if url:
        # Standardize postgres:// to postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Default to localhost postgres
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_caller")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine(db_url: str | None = None, echo: bool = False) -> AsyncEngine:
    """Get or create singleton AsyncEngine."""
    global _engine, _sessionmaker
    if _engine is None or db_url is not None:
        url = db_url or get_database_url()
        logger.info(
            "Initializing async database engine: %s", url.split("@")[-1] if "@" in url else url
        )
        _engine = create_async_engine(
            url,
            echo=echo,
            future=True,
            pool_pre_ping=True if "sqlite" not in url else False,
        )
        _sessionmaker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


def get_session_maker(db_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    """Get async sessionmaker instance."""
    global _sessionmaker
    if _sessionmaker is None or db_url is not None:
        get_engine(db_url=db_url)
    assert _sessionmaker is not None
    return _sessionmaker


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency yielding a scoped database session."""
    session_factory = get_session_maker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Create all declarative tables if they do not already exist."""
    eng = engine or get_engine()
    async with eng.begin() as conn:
        # Enable vector extension on postgres
        if eng.dialect.name == "postgresql":
            try:
                from sqlalchemy import text

                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as e:
                logger.warning(
                    "Could not create vector extension (may already exist or missing privileges): %s",
                    e,
                )
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schemas initialized successfully")
