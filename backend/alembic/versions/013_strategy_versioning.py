"""Add strategy versioning table

Stores config snapshots when strategies are updated, enabling
change history and rollback capabilities.

Revision ID: 013
Revises: 012
Create Date: 2026-02-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "strategy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("symbols", postgresql.JSON, server_default="'[]'"),
        sa.Column("config", postgresql.JSON, server_default="'{}'"),
        sa.Column("change_note", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_strategy_versions_strategy_id", "strategy_versions", ["strategy_id"])
    op.create_index(
        "ix_strategy_versions_unique",
        "strategy_versions",
        ["strategy_id", "version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("strategy_versions")
