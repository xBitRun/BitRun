"""Add trade_type to agents

Revision ID: 020
Revises: 019
Create Date: 2026-02-19
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "020"
down_revision: Union[str, None] = "019"


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "trade_type",
            sa.String(20),
            nullable=False,
            server_default="crypto_perp"
        )
    )


def downgrade() -> None:
    op.drop_column("agents", "trade_type")
