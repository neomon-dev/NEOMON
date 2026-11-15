"""Widen evidence_type and extraction_method columns for PostgreSQL compatibility.

Revision ID: 20261115_0017
Revises: 20261114_0016
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20261115_0017"
down_revision = "20261114_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("evidence") as batch_op:
            batch_op.alter_column(
                "evidence_type",
                existing_type=sa.String(length=24),
                type_=sa.String(length=64),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "extraction_method",
                existing_type=sa.String(length=80),
                type_=sa.String(length=120),
                existing_nullable=False,
            )
    else:
        # PostgreSQL native ALTER COLUMN
        op.execute("ALTER TABLE evidence ALTER COLUMN evidence_type TYPE VARCHAR(64)")
        op.execute("ALTER TABLE evidence ALTER COLUMN extraction_method TYPE VARCHAR(120)")


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("evidence") as batch_op:
            batch_op.alter_column(
                "evidence_type",
                existing_type=sa.String(length=64),
                type_=sa.String(length=24),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "extraction_method",
                existing_type=sa.String(length=120),
                type_=sa.String(length=80),
                existing_nullable=False,
            )
    else:
        op.execute("ALTER TABLE evidence ALTER COLUMN evidence_type TYPE VARCHAR(24)")
        op.execute("ALTER TABLE evidence ALTER COLUMN extraction_method TYPE VARCHAR(80)")
