"""Add market_snapshot JSON column to decision_records

Revision ID: 005
Revises: 004
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add market_snapshot column to decision_records.

    This column stores the structured market data snapshot (JSON) that was
    used for each AI decision, including exchange name, prices, technical
    indicators, and recent K-lines.
    """
    op.add_column(
        'decision_records',
        sa.Column('market_snapshot', sa.JSON, nullable=True),
    )


def downgrade() -> None:
    """Drop market_snapshot column from decision_records."""
    op.drop_column('decision_records', 'market_snapshot')
