"""Add debate configuration to agents

Migrates debate configuration from Strategy to Agent model.
This allows users to configure multi-model debate when creating
trading agents.

- Add debate_enabled to agents (default: false)
- Add debate_models to agents (json array, nullable)
- Add debate_consensus_mode to agents (string, nullable)
- Add debate_min_participants to agents (default: 2)

Revision ID: 019
Revises: 018
Create Date: 2026-02-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add debate configuration columns to agents table
    op.add_column(
        "agents",
        sa.Column(
            "debate_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false"
        )
    )
    op.add_column(
        "agents",
        sa.Column(
            "debate_models",
            postgresql.JSON(),
            nullable=True
        )
    )
    op.add_column(
        "agents",
        sa.Column(
            "debate_consensus_mode",
            sa.String(50),
            nullable=True
        )
    )
    op.add_column(
        "agents",
        sa.Column(
            "debate_min_participants",
            sa.Integer(),
            nullable=False,
            server_default="2"
        )
    )


def downgrade() -> None:
    op.drop_column("agents", "debate_min_participants")
    op.drop_column("agents", "debate_consensus_mode")
    op.drop_column("agents", "debate_models")
    op.drop_column("agents", "debate_enabled")
