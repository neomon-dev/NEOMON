"""Database configuration and session management for NEOMON.

Supports production PostgreSQL (postgresql+asyncpg) and local SQLite (sqlite+aiosqlite).
Enforces connection pooling, pre-ping verification, and transaction rollback boundaries.
"""

from collections.abc import AsyncIterator
import time
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def build_async_engine(
    database_url: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> AsyncEngine:
    """Build and configure an AsyncEngine with appropriate pooling for the dialect."""
    cfg = settings or get_settings()
    url = database_url or cfg.database_url

    is_sqlite = url.startswith("sqlite")
    is_postgres = "postgresql" in url

    kwargs: Dict[str, Any] = {
        "echo": cfg.debug,
        "pool_pre_ping": cfg.database_pool_pre_ping,
    }

    if is_sqlite:
        kwargs["connect_args"] = {"timeout": 30, "check_same_thread": False}
    elif is_postgres:
        kwargs["pool_size"] = cfg.database_pool_size
        kwargs["max_overflow"] = cfg.database_max_overflow
        kwargs["pool_timeout"] = cfg.database_pool_timeout
        kwargs["pool_recycle"] = cfg.database_pool_recycle

    created_engine = create_async_engine(url, **kwargs)

    if is_sqlite:
        @event.listens_for(created_engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.close()

    return created_engine


settings = get_settings()
engine: AsyncEngine = build_async_engine(settings.database_url, settings)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
async_session_factory = SessionFactory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a transactional asynchronous database session with automatic rollback on error."""
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_database_health(db_engine: Optional[AsyncEngine] = None) -> Dict[str, Any]:
    """Execute active database health probe, measure latency, and inspect pool status."""
    active_engine = db_engine or engine
    dialect_name = active_engine.dialect.name
    pool = active_engine.pool

    start_time = time.perf_counter()
    try:
        async with active_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if val != 1:
                return {
                    "healthy": False,
                    "status": "degraded",
                    "dialect": dialect_name,
                    "latency_ms": latency_ms,
                    "error": f"Unexpected health probe return value: {val}",
                }

        pool_stats: Dict[str, Any] = {
            "dialect": dialect_name,
            "pre_ping": getattr(active_engine.pool, "_pre_ping", True),
        }
        if hasattr(pool, "size"):
            pool_stats["size"] = pool.size()
        if hasattr(pool, "checkedin"):
            pool_stats["checkedin"] = pool.checkedin()
        if hasattr(pool, "checkedout"):
            pool_stats["checkedout"] = pool.checkedout()
        if hasattr(pool, "overflow"):
            pool_stats["overflow"] = pool.overflow()

        return {
            "healthy": True,
            "status": "healthy",
            "dialect": dialect_name,
            "latency_ms": latency_ms,
            "pool": pool_stats,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "healthy": False,
            "status": "unhealthy",
            "dialect": dialect_name,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


async def close_database() -> None:
    """Dispose of the database engine and close all pooled connections."""
    await engine.dispose()
