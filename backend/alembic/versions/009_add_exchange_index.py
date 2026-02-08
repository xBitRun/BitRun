"""Add index on exchange_accounts.exchange column.

Improves query performance when filtering accounts by exchange type.

Revision ID: 009
Revises: 008
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_exchange_accounts_exchange",
        "exchange_accounts",
        ["exchange"],
    )


def downgrade() -> None:
    op.drop_index("ix_exchange_accounts_exchange", table_name="exchange_accounts")
