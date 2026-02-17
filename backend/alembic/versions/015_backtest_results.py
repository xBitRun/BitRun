"""Add backtest results table

Adds backtest_results table for persisting backtest records.
Allows users to review past backtests and compare strategy performance.

Revision ID: 015
Revises: 014
Create Date: 2026-02-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="SET NULL"),
                  nullable=True),
        # Configuration snapshot
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("symbols", postgresql.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("exchange", sa.String(50), nullable=False,
                  server_default=sa.text("'hyperliquid'")),
        sa.Column("initial_balance", sa.Float, nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False,
                  server_default=sa.text("'1h'")),
        sa.Column("use_ai", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        # Time range
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        # Core metrics
        sa.Column("final_balance", sa.Float, nullable=False),
        sa.Column("total_return_percent", sa.Float, nullable=False),
        sa.Column("total_trades", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("winning_trades", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("losing_trades", sa.Integer, nullable=False,
                  server_default="0"),
        sa.Column("win_rate", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("profit_factor", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("max_drawdown_percent", sa.Float, nullable=False,
                  server_default="0.0"),
        sa.Column("sharpe_ratio", sa.Float, nullable=True),
        sa.Column("sortino_ratio", sa.Float, nullable=True),
        sa.Column("calmar_ratio", sa.Float, nullable=True),
        sa.Column("total_fees", sa.Float, nullable=False,
                  server_default="0.0"),
        # Full result data
        sa.Column("equity_curve", postgresql.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("drawdown_curve", postgresql.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("trades", postgresql.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("monthly_returns", postgresql.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("trade_statistics", postgresql.JSON(), nullable=True),
        sa.Column("symbol_breakdown", postgresql.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("analysis", postgresql.JSON(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_backtest_results_user_id",
                     "backtest_results", ["user_id"])
    op.create_index("ix_backtest_results_strategy_id",
                     "backtest_results", ["strategy_id"])
    op.create_index("ix_backtest_results_created_at",
                     "backtest_results", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_backtest_results_created_at")
    op.drop_index("ix_backtest_results_strategy_id")
    op.drop_index("ix_backtest_results_user_id")
    op.drop_table("backtest_results")
