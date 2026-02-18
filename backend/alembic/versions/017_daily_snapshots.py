"""Add daily snapshots tables

Adds daily_account_snapshots and daily_agent_snapshots tables for
tracking historical equity and performance metrics over time.
Enables equity curve visualization and period-based P&L analysis.

Revision ID: 017
Revises: 016
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Daily account snapshots
    op.create_table(
        "daily_account_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exchange_accounts.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        # Equity components
        sa.Column("equity", sa.Float, nullable=False),
        sa.Column("available_balance", sa.Float, nullable=False),
        sa.Column("unrealized_pnl", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("margin_used", sa.Float, nullable=False,
                  server_default="0.0"),
        # Daily P&L
        sa.Column("daily_pnl", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("daily_pnl_percent", sa.Float, nullable=False,
                  server_default="0.0"),
        # Position summary
        sa.Column("open_positions", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("position_summary", postgresql.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        # Metadata
        sa.Column("snapshot_source", sa.String(20), nullable=False,
                  server_default=sa.text("'scheduled'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        # Unique constraint: one snapshot per account per day
        sa.UniqueConstraint("account_id", "snapshot_date",
                            name="uq_daily_account_snapshots_account_date"),
    )
    op.create_index("ix_daily_account_snapshots_user_id",
                     "daily_account_snapshots", ["user_id"])
    op.create_index("ix_daily_account_snapshots_account_id",
                     "daily_account_snapshots", ["account_id"])
    op.create_index("ix_daily_account_snapshots_date",
                     "daily_account_snapshots", ["snapshot_date"])

    # Daily agent snapshots
    op.create_table(
        "daily_agent_snapshots",
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
        sa.Column("snapshot_date", sa.Date, nullable=False),
        # Cumulative metrics
        sa.Column("total_pnl", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("total_trades", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("winning_trades", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("losing_trades", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("max_drawdown", sa.Float, nullable=False,
                  server_default="0.0"),
        # Daily metrics
        sa.Column("daily_pnl", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("daily_trades", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("daily_winning", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("daily_losing", sa.Integer, nullable=False,
                  server_default="0"),
        # Virtual equity (for mock agents)
        sa.Column("virtual_equity", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        # Unique constraint: one snapshot per agent per day
        sa.UniqueConstraint("agent_id", "snapshot_date",
                            name="uq_daily_agent_snapshots_agent_date"),
    )
    op.create_index("ix_daily_agent_snapshots_user_id",
                     "daily_agent_snapshots", ["user_id"])
    op.create_index("ix_daily_agent_snapshots_agent_id",
                     "daily_agent_snapshots", ["agent_id"])
    op.create_index("ix_daily_agent_snapshots_date",
                     "daily_agent_snapshots", ["snapshot_date"])


def downgrade() -> None:
    # Drop daily_agent_snapshots
    op.drop_index("ix_daily_agent_snapshots_date")
    op.drop_index("ix_daily_agent_snapshots_agent_id")
    op.drop_index("ix_daily_agent_snapshots_user_id")
    op.drop_table("daily_agent_snapshots")

    # Drop daily_account_snapshots
    op.drop_index("ix_daily_account_snapshots_date")
    op.drop_index("ix_daily_account_snapshots_account_id")
    op.drop_index("ix_daily_account_snapshots_user_id")
    op.drop_table("daily_account_snapshots")
