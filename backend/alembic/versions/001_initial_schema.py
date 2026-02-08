"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Create exchange_accounts table
    op.create_table(
        'exchange_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('exchange', sa.String(50), nullable=False),
        sa.Column('is_testnet', sa.Boolean(), nullable=False, default=False),
        sa.Column('encrypted_api_key', sa.Text(), nullable=True),
        sa.Column('encrypted_api_secret', sa.Text(), nullable=True),
        sa.Column('encrypted_private_key', sa.Text(), nullable=True),
        sa.Column('encrypted_passphrase', sa.Text(), nullable=True),
        sa.Column('is_connected', sa.Boolean(), nullable=False, default=False),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('connection_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_exchange_accounts_user_id', 'exchange_accounts', ['user_id'])
    
    # Create strategies table
    op.create_table(
        'strategies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('trading_mode', sa.String(20), nullable=False, default='conservative'),
        sa.Column('config', postgresql.JSON(), default=dict),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('total_pnl', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('winning_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('losing_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('max_drawdown', sa.Float(), nullable=False, default=0.0),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['exchange_accounts.id'], ondelete='SET NULL')
    )
    op.create_index('ix_strategies_user_id', 'strategies', ['user_id'])
    op.create_index('ix_strategies_account_id', 'strategies', ['account_id'])
    op.create_index('ix_strategies_status', 'strategies', ['status'])
    
    # Create decision_records table
    op.create_table(
        'decision_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt', sa.Text(), nullable=False),
        sa.Column('raw_response', sa.Text(), nullable=False),
        sa.Column('chain_of_thought', sa.Text(), default=''),
        sa.Column('market_assessment', sa.Text(), default=''),
        sa.Column('decisions', postgresql.JSON(), default=list),
        sa.Column('overall_confidence', sa.Integer(), nullable=False, default=0),
        sa.Column('executed', sa.Boolean(), nullable=False, default=False),
        sa.Column('execution_results', postgresql.JSON(), default=list),
        sa.Column('ai_model', sa.String(100), default=''),
        sa.Column('tokens_used', sa.Integer(), nullable=False, default=0),
        sa.Column('latency_ms', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE')
    )
    op.create_index('ix_decision_records_strategy_id', 'decision_records', ['strategy_id'])
    op.create_index('ix_decision_records_timestamp', 'decision_records', ['timestamp'])


def downgrade() -> None:
    op.drop_table('decision_records')
    op.drop_table('strategies')
    op.drop_table('exchange_accounts')
    op.drop_table('users')
