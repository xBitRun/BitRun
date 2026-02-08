"""Add ai_model column to strategies table

Revision ID: 002
Revises: 001
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add ai_model column to strategies table.

    This column stores the AI model identifier in format 'provider:model_id',
    e.g., 'anthropic:claude-sonnet-4-5-20250514' or 'openai:gpt-4o'.

    If NULL, the strategy uses the global default model from settings.
    """
    op.add_column(
        'strategies',
        sa.Column(
            'ai_model',
            sa.String(100),
            nullable=True,
            default=None,
            comment='AI model identifier (provider:model_id format). NULL uses global default.'
        )
    )


def downgrade() -> None:
    """Remove ai_model column from strategies table."""
    op.drop_column('strategies', 'ai_model')
