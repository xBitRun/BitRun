"""Add worker heartbeat fields to agents

Adds heartbeat tracking fields to support worker health monitoring
and automatic recovery from crashes.

- Add worker_heartbeat_at to agents (timestamp, nullable)
- Add worker_instance_id to agents (string, nullable)
- Add partial index on heartbeat for active agents

Revision ID: 020
Revises: 019
Create Date: 2026-02-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add heartbeat timestamp column
    op.add_column(
        "agents",
        sa.Column(
            "worker_heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=True
        )
    )

    # Add worker instance identifier column
    op.add_column(
        "agents",
        sa.Column(
            "worker_instance_id",
            sa.String(100),
            nullable=True
        )
    )

    # Create partial index for active agents to efficiently query stale workers
    # This index only includes rows where status = 'active'
    op.execute(
        """
        CREATE INDEX ix_agents_worker_heartbeat_active
        ON agents (worker_heartbeat_at)
        WHERE status = 'active'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agents_worker_heartbeat_active")
    op.drop_column("agents", "worker_instance_id")
    op.drop_column("agents", "worker_heartbeat_at")
