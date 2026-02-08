"""Add ai_provider_configs table for user-level AI provider configuration

Revision ID: 003
Revises: 002
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create ai_provider_configs table.

    This table stores user-level AI provider configurations including:
    - Provider type (anthropic, openai, deepseek, etc.)
    - Display name and notes
    - Encrypted API key
    - Base URL for API endpoint
    - API format (anthropic, openai, custom)
    """
    op.create_table(
        'ai_provider_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('website_url', sa.String(500), nullable=True),
        sa.Column('encrypted_api_key', sa.Text, nullable=True),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('api_format', sa.String(50), nullable=False, server_default='openai'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )

    # Create index for faster lookups by user_id and provider_type
    op.create_index(
        'ix_ai_provider_configs_user_provider',
        'ai_provider_configs',
        ['user_id', 'provider_type']
    )


def downgrade() -> None:
    """Drop ai_provider_configs table."""
    op.drop_index('ix_ai_provider_configs_user_provider', table_name='ai_provider_configs')
    op.drop_table('ai_provider_configs')
