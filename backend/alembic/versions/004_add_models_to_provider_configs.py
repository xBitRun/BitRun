"""Add models JSON column to ai_provider_configs

Revision ID: 004
Revises: 003
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add models column to ai_provider_configs.

    This column stores a JSON array of model configurations per provider.
    Each item contains model id, display name, context window, etc.
    """
    op.add_column(
        'ai_provider_configs',
        sa.Column('models', sa.Text, nullable=True),
    )


def downgrade() -> None:
    """Drop models column from ai_provider_configs."""
    op.drop_column('ai_provider_configs', 'models')
