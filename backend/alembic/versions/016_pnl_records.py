"""Add P&L records table

Adds pnl_records table for tracking individual trade profit/loss.
Records are created when positions are closed, enabling detailed
trade history and performance analysis.

Revision ID: 016
Revises: 015
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pnl_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exchange_accounts.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agent_positions.id", ondelete="SET NULL"),
                  nullable=True),
        # Trade details
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),  # 'long' | 'short'
        sa.Column("realized_pnl", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("fees", sa.Float, nullable=False,
                  server_default="0.0"),
        # Price and size
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("size", sa.Float, nullable=False),
        sa.Column("size_usd", sa.Float, nullable=False),
        sa.Column("leverage", sa.Integer, nullable=False,
                  server_default="1"),
        # Timing
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("exit_reason", sa.String(50), nullable=True),
        # Metadata
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    # Indexes for common query patterns
    op.create_index("ix_pnl_records_user_id", "pnl_records", ["user_id"])
    op.create_index("ix_pnl_records_agent_id", "pnl_records", ["agent_id"])
    op.create_index("ix_pnl_records_account_id", "pnl_records", ["account_id"])
    op.create_index("ix_pnl_records_closed_at", "pnl_records", ["closed_at"])
    op.create_index("ix_pnl_records_symbol", "pnl_records", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_pnl_records_symbol")
    op.drop_index("ix_pnl_records_closed_at")
    op.drop_index("ix_pnl_records_account_id")
    op.drop_index("ix_pnl_records_agent_id")
    op.drop_index("ix_pnl_records_user_id")
    op.drop_table("pnl_records")
