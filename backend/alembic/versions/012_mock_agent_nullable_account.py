"""Make agent_positions.account_id nullable for mock agents.

Mock agents have no exchange account, so account_id must be nullable.
Also changes the FK ondelete from CASCADE to SET NULL.

Revision ID: 012
Revises: 011
Create Date: 2026-02-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make account_id nullable for mock agents
    op.alter_column(
        "agent_positions",
        "account_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Update FK constraint: CASCADE -> SET NULL
    op.drop_constraint(
        "agent_positions_account_id_fkey",
        "agent_positions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "agent_positions_account_id_fkey",
        "agent_positions",
        "exchange_accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Revert FK to CASCADE
    op.drop_constraint(
        "agent_positions_account_id_fkey",
        "agent_positions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "agent_positions_account_id_fkey",
        "agent_positions",
        "exchange_accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Make account_id non-nullable again (will fail if NULL values exist)
    op.alter_column(
        "agent_positions",
        "account_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
