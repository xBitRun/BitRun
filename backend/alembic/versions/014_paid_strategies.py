"""Add paid strategies support

Adds pricing fields to strategies table and creates
strategy_subscriptions table for tracking paid access.

Revision ID: 014
Revises: 013
Create Date: 2026-02-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pricing fields to strategies
    op.add_column("strategies", sa.Column(
        "is_paid", sa.Boolean, server_default=sa.false(), nullable=False
    ))
    op.add_column("strategies", sa.Column(
        "price_monthly", sa.Float, nullable=True
    ))
    op.add_column("strategies", sa.Column(
        "revenue_share_percent", sa.Float, server_default="0.0", nullable=False
    ))
    op.add_column("strategies", sa.Column(
        "pricing_model", sa.String(20), server_default=sa.text("'free'"), nullable=False
    ))

    # Create subscriptions table
    op.create_table(
        "strategy_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default=sa.text("'active'")),
        sa.Column("price_paid", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("pricing_model", sa.String(20), nullable=False,
                  server_default=sa.text("'free'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_strategy_subscriptions_strategy_id",
                     "strategy_subscriptions", ["strategy_id"])
    op.create_index("ix_strategy_subscriptions_user_id",
                     "strategy_subscriptions", ["user_id"])
    # Unique constraint: one active subscription per user+strategy
    op.create_index(
        "ix_strategy_subscriptions_unique_active",
        "strategy_subscriptions",
        ["strategy_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_table("strategy_subscriptions")
    op.drop_column("strategies", "pricing_model")
    op.drop_column("strategies", "revenue_share_percent")
    op.drop_column("strategies", "price_monthly")
    op.drop_column("strategies", "is_paid")
