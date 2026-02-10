"""Add multi-model debate fields to decision_records

Adds columns for storing debate mode metadata: whether a decision
used multi-model debate, which models participated, their individual
responses, the consensus mode, and the agreement score.

Revision ID: 010
Revises: 009
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add debate-related columns to decision_records."""
    op.add_column(
        "decision_records",
        sa.Column("is_debate", sa.Boolean, server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "decision_records",
        sa.Column("debate_models", sa.JSON, nullable=True),
    )
    op.add_column(
        "decision_records",
        sa.Column("debate_responses", sa.JSON, nullable=True),
    )
    op.add_column(
        "decision_records",
        sa.Column("debate_consensus_mode", sa.String(50), nullable=True),
    )
    op.add_column(
        "decision_records",
        sa.Column("debate_agreement_score", sa.Float, nullable=True),
    )


def downgrade() -> None:
    """Drop debate-related columns from decision_records."""
    op.drop_column("decision_records", "debate_agreement_score")
    op.drop_column("decision_records", "debate_consensus_mode")
    op.drop_column("decision_records", "debate_responses")
    op.drop_column("decision_records", "debate_models")
    op.drop_column("decision_records", "is_debate")
