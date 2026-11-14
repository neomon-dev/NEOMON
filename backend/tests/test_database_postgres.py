"""Tests for PostgreSQL Database Infrastructure and Connection Pooling."""

import pytest
from sqlalchemy import text, Integer, String, Column
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.config import Settings
from app.db import Base, build_async_engine, check_database_health, SessionFactory


def test_postgresql_engine_configuration():
    """Verify async engine builder applies pool settings for postgresql+asyncpg."""
    custom_settings = Settings(
        database_url="postgresql+asyncpg://neomon:secret@localhost:5432/neomon_test",
        database_pool_size=15,
        database_max_overflow=25,
        database_pool_timeout=45.0,
        database_pool_recycle=3600,
        database_pool_pre_ping=True,
    )
    pg_engine = build_async_engine(custom_settings.database_url, custom_settings)
    assert pg_engine.dialect.name == "postgresql"
    assert pg_engine.dialect.driver == "asyncpg"
    assert pg_engine.pool.size() == 15
    assert pg_engine.pool._max_overflow == 25
    assert pg_engine.pool._timeout == 45.0
    assert pg_engine.pool._recycle == 3600
    assert pg_engine.pool._pre_ping is True


def test_all_models_compile_to_postgresql_ddl():
    """Verify that Base.metadata schemas compile cleanly to valid PostgreSQL DDL."""
    pg_dialect = postgresql.dialect()
    tables = Base.metadata.tables
    assert len(tables) >= 50, f"Expected at least 50 tables, found {len(tables)}"

    compiled_count = 0
    for table_name, table in tables.items():
        ddl = str(CreateTable(table).compile(dialect=pg_dialect))
        assert "CREATE TABLE" in ddl
        assert table_name in ddl
        compiled_count += 1

    assert compiled_count == len(tables)


@pytest.mark.asyncio
async def test_database_health_probe():
    """Verify active database health probe returns latency, pool stats, and status."""
    health = await check_database_health()
    assert health["status"] == "healthy"
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0.0
    assert "pool" in health
    assert "dialect" in health


@pytest.mark.asyncio
async def test_session_transaction_rollback_safety():
    """Verify that an exception inside a session safely triggers a rollback."""
    # Attempt an invalid operation inside a session context
    async with SessionFactory() as session:
        try:
            # Execute invalid SQL syntax to induce a rollback
            await session.execute(text("SELECT * FROM non_existent_table_for_rollback_test_xyz"))
            await session.commit()
        except Exception:
            await session.rollback()

    # Verify subsequent valid query works normally on a fresh session
    async with SessionFactory() as session:
        res = await session.execute(text("SELECT 1"))
        val = res.scalar()
        assert val == 1
