"""Add strategy_positions table and capital allocation fields.

Implements multi-strategy position isolation:
- New strategy_positions table with partial unique index
- allocated_capital / allocated_capital_percent on strategies and quant_strategies

Revision ID: 008
Revises: 007
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Create strategy_positions table ---
    op.create_table(
        'strategy_positions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('strategy_type', sa.String(10), nullable=False),
        sa.Column(
            'account_id',
            UUID(as_uuid=True),
            sa.ForeignKey('exchange_accounts.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('size', sa.Float, server_default='0.0'),
        sa.Column('size_usd', sa.Float, server_default='0.0'),
        sa.Column('entry_price', sa.Float, server_default='0.0'),
        sa.Column('leverage', sa.Integer, server_default='1'),
        sa.Column('status', sa.String(10), server_default='pending', index=True),
        sa.Column('realized_pnl', sa.Float, server_default='0.0'),
        sa.Column('close_price', sa.Float, nullable=True),
        sa.Column('opened_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('closed_at', sa.DateTime, nullable=True),
    )

    # Partial unique index: one open/pending position per account+symbol
    op.create_index(
        'ix_strategy_positions_unique_open',
        'strategy_positions',
        ['account_id', 'symbol'],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'pending')"),
    )

    # --- 2. Add capital allocation columns to strategies ---
    op.add_column(
        'strategies',
        sa.Column('allocated_capital', sa.Float, nullable=True),
    )
    op.add_column(
        'strategies',
        sa.Column('allocated_capital_percent', sa.Float, nullable=True),
    )

    # --- 3. Add capital allocation columns to quant_strategies ---
    op.add_column(
        'quant_strategies',
        sa.Column('allocated_capital', sa.Float, nullable=True),
    )
    op.add_column(
        'quant_strategies',
        sa.Column('allocated_capital_percent', sa.Float, nullable=True),
    )


def downgrade() -> None:
    # Remove capital allocation columns
    op.drop_column('quant_strategies', 'allocated_capital_percent')
    op.drop_column('quant_strategies', 'allocated_capital')
    op.drop_column('strategies', 'allocated_capital_percent')
    op.drop_column('strategies', 'allocated_capital')

    # Drop the partial unique index first, then the table
    op.drop_index('ix_strategy_positions_unique_open', 'strategy_positions')
    op.drop_table('strategy_positions')
