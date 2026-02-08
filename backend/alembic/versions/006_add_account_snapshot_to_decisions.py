"""Add account_snapshot JSON column to decision_records

Revision ID: 006
Revises: 005
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add account_snapshot column to decision_records.

    This column stores the account state snapshot (JSON) at the time of
    each AI decision, including equity, balance, margin, unrealized P/L,
    and open positions.
    """
    op.add_column(
        'decision_records',
        sa.Column('account_snapshot', sa.JSON, nullable=True),
    )


def downgrade() -> None:
    """Drop account_snapshot column from decision_records."""
    op.drop_column('decision_records', 'account_snapshot')
