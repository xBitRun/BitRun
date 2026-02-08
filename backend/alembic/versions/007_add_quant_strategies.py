"""Add quant_strategies table for traditional quantitative trading strategies

Revision ID: 007
Revises: 006
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create quant_strategies table for Grid, DCA, and RSI strategies.
    """
    op.create_table(
        'quant_strategies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('exchange_accounts.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, server_default=''),
        sa.Column('strategy_type', sa.String(20), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('config', JSON, server_default='{}'),
        sa.Column('runtime_state', JSON, server_default='{}'),
        sa.Column('status', sa.String(20), server_default='draft', index=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('total_pnl', sa.Float, server_default='0.0'),
        sa.Column('total_trades', sa.Integer, server_default='0'),
        sa.Column('winning_trades', sa.Integer, server_default='0'),
        sa.Column('losing_trades', sa.Integer, server_default='0'),
        sa.Column('max_drawdown', sa.Float, server_default='0.0'),
        sa.Column('last_run_at', sa.DateTime, nullable=True),
        sa.Column('next_run_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop quant_strategies table."""
    op.drop_table('quant_strategies')
