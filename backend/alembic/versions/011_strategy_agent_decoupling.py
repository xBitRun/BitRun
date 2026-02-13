"""Strategy/Agent decoupling: unified strategies + execution agents

Major architectural refactoring:
1. Unify AI strategies (strategies) and quant strategies (quant_strategies)
   into a single strategies table with a type discriminator.
2. Create agents table for execution instances (Strategy + Model + Account).
3. Create agent_positions table replacing strategy_positions with
   agent-level isolation (unique constraint on agent_id+symbol).
4. Migrate decision_records from strategy_id to agent_id.
5. Migrate all existing data.

Revision ID: 011
Revises: 010
Create Date: 2026-02-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Execute the Strategy/Agent decoupling migration."""

    # =========================================================================
    # Step 1: Create agents table
    # =========================================================================
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column("execution_mode", sa.String(20), nullable=False, server_default="live"),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exchange_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mock_initial_balance", sa.Float, nullable=True),
        sa.Column("allocated_capital", sa.Float, nullable=True),
        sa.Column("allocated_capital_percent", sa.Float, nullable=True),
        sa.Column("execution_interval_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("auto_execute", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("runtime_state", postgresql.JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("total_pnl", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("winning_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("losing_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_drawdown", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_agents_user_id", "agents", ["user_id"])
    op.create_index("ix_agents_strategy_id", "agents", ["strategy_id"])
    op.create_index("ix_agents_account_id", "agents", ["account_id"])
    op.create_index("ix_agents_status", "agents", ["status"])

    # =========================================================================
    # Step 2: Create agent_positions table
    # =========================================================================
    op.create_table(
        "agent_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exchange_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("size", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("size_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("entry_price", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("leverage", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(10), nullable=False, server_default="'pending'"),
        sa.Column("realized_pnl", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("close_price", sa.Float, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_positions_agent_id", "agent_positions", ["agent_id"])
    op.create_index("ix_agent_positions_account_id", "agent_positions", ["account_id"])
    op.create_index("ix_agent_positions_status", "agent_positions", ["status"])
    # Partial unique index: one open/pending position per agent+symbol
    op.create_index(
        "ix_agent_positions_unique_open",
        "agent_positions",
        ["agent_id", "symbol"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'pending')"),
    )

    # =========================================================================
    # Step 3: Add new columns to strategies table
    # =========================================================================
    # Add type column (will be populated in data migration)
    op.add_column("strategies", sa.Column("type", sa.String(20), nullable=True))
    # Add symbols as JSON (will be populated from config.symbols or quant symbol)
    op.add_column("strategies", sa.Column("symbols", postgresql.JSON, server_default="'[]'"))
    # Add marketplace fields
    op.add_column("strategies", sa.Column(
        "visibility", sa.String(20), server_default="'private'", nullable=False
    ))
    op.add_column("strategies", sa.Column("category", sa.String(50), nullable=True))
    op.add_column("strategies", sa.Column(
        "tags", postgresql.JSON, server_default="'[]'"
    ))
    op.add_column("strategies", sa.Column(
        "forked_from", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    ))
    op.add_column("strategies", sa.Column(
        "fork_count", sa.Integer, server_default="0", nullable=False
    ))

    # Add agent_id column to decision_records (will be populated, then made NOT NULL)
    op.add_column("decision_records", sa.Column(
        "agent_id", postgresql.UUID(as_uuid=True), nullable=True
    ))

    # =========================================================================
    # Step 4: Data migration - AI strategies
    # =========================================================================
    # For each existing AI strategy, set type='ai' and create a corresponding agent
    conn = op.get_bind()

    # 4a. Set type='ai' for all existing strategies
    conn.execute(sa.text("UPDATE strategies SET type = 'ai'"))

    # 4b. Move symbols from config->symbols to top-level symbols column
    # The config JSON has a "symbols" key with a list like ["BTC", "ETH"]
    conn.execute(sa.text("""
        UPDATE strategies
        SET symbols = COALESCE(config->'symbols', '["BTC", "ETH"]'::jsonb)
        WHERE type = 'ai'
    """))

    # 4c. Merge prompt and trading_mode into config for AI strategies
    # Move the top-level prompt into config.prompt
    conn.execute(sa.text("""
        UPDATE strategies
        SET config = jsonb_set(
            COALESCE(config::jsonb, '{}'::jsonb),
            '{prompt}',
            to_jsonb(COALESCE(prompt, ''))
        )
        WHERE type = 'ai' AND prompt IS NOT NULL
    """))
    # Move trading_mode into config
    conn.execute(sa.text("""
        UPDATE strategies
        SET config = jsonb_set(
            COALESCE(config::jsonb, '{}'::jsonb),
            '{trading_mode}',
            to_jsonb(COALESCE(trading_mode, 'conservative'))
        )
        WHERE type = 'ai'
    """))

    # 4d. Create agents from existing AI strategies
    conn.execute(sa.text("""
        INSERT INTO agents (
            id, user_id, name, strategy_id, ai_model,
            execution_mode, account_id, mock_initial_balance,
            allocated_capital, allocated_capital_percent,
            execution_interval_minutes, auto_execute,
            status, error_message,
            total_pnl, total_trades, winning_trades, losing_trades, max_drawdown,
            last_run_at, next_run_at, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            user_id,
            name,
            id,  -- strategy_id = original strategy id
            ai_model,
            CASE WHEN account_id IS NOT NULL THEN 'live' ELSE 'mock' END,
            account_id,
            CASE WHEN account_id IS NULL THEN 10000.0 ELSE NULL END,
            allocated_capital,
            allocated_capital_percent,
            COALESCE((config->>'execution_interval_minutes')::int, 30),
            COALESCE((config->>'auto_execute')::boolean, true),
            status,
            error_message,
            total_pnl, total_trades, winning_trades, losing_trades, max_drawdown,
            last_run_at, next_run_at, created_at, updated_at
        FROM strategies
        WHERE type = 'ai'
    """))

    # =========================================================================
    # Step 5: Data migration - Quant strategies
    # =========================================================================
    # 5a. Insert quant strategies into unified strategies table
    conn.execute(sa.text("""
        INSERT INTO strategies (
            id, user_id, type, name, description,
            symbols, config,
            visibility, tags, fork_count,
            created_at, updated_at
        )
        SELECT
            id, user_id, strategy_type, name, description,
            jsonb_build_array(symbol),
            config::jsonb,
            'private', '[]'::jsonb, 0,
            created_at, updated_at
        FROM quant_strategies
    """))

    # 5b. Create agents for quant strategies
    conn.execute(sa.text("""
        INSERT INTO agents (
            id, user_id, name, strategy_id, ai_model,
            execution_mode, account_id, mock_initial_balance,
            allocated_capital, allocated_capital_percent,
            execution_interval_minutes, auto_execute,
            runtime_state,
            status, error_message,
            total_pnl, total_trades, winning_trades, losing_trades, max_drawdown,
            last_run_at, next_run_at, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            user_id,
            name,
            id,  -- strategy_id = quant strategy id (same id reused)
            NULL,  -- no AI model for quant
            CASE WHEN account_id IS NOT NULL THEN 'live' ELSE 'mock' END,
            account_id,
            CASE WHEN account_id IS NULL THEN 10000.0 ELSE NULL END,
            allocated_capital,
            allocated_capital_percent,
            30,  -- default interval
            true,
            runtime_state,
            status,
            error_message,
            total_pnl, total_trades, winning_trades, losing_trades, max_drawdown,
            last_run_at, next_run_at, created_at, updated_at
        FROM quant_strategies
    """))

    # =========================================================================
    # Step 6: Migrate decision_records (strategy_id -> agent_id)
    # =========================================================================
    # Map decision_records.strategy_id to the corresponding agent_id
    conn.execute(sa.text("""
        UPDATE decision_records dr
        SET agent_id = a.id
        FROM agents a
        WHERE a.strategy_id = dr.strategy_id
    """))

    # =========================================================================
    # Step 7: Migrate strategy_positions -> agent_positions
    # =========================================================================
    # Map strategy_positions to agent_positions using the strategy->agent mapping
    conn.execute(sa.text("""
        INSERT INTO agent_positions (
            id, agent_id, account_id,
            symbol, side, size, size_usd, entry_price, leverage,
            status, realized_pnl, close_price,
            opened_at, closed_at
        )
        SELECT
            sp.id,
            a.id,  -- agent_id from the mapped agent
            sp.account_id,
            sp.symbol, sp.side, sp.size, sp.size_usd, sp.entry_price, sp.leverage,
            sp.status, sp.realized_pnl, sp.close_price,
            sp.opened_at, sp.closed_at
        FROM strategy_positions sp
        JOIN agents a ON a.strategy_id = sp.strategy_id
    """))

    # =========================================================================
    # Step 8: Make type NOT NULL, add index
    # =========================================================================
    op.alter_column("strategies", "type", nullable=False)
    op.create_index("ix_strategies_type", "strategies", ["type"])

    # Make agent_id NOT NULL on decision_records (all rows should be populated now)
    # First add FK constraint
    op.create_foreign_key(
        "fk_decision_records_agent_id",
        "decision_records", "agents",
        ["agent_id"], ["id"],
        ondelete="CASCADE"
    )
    op.create_index("ix_decision_records_agent_id", "decision_records", ["agent_id"])

    # =========================================================================
    # Step 9: Drop old columns from strategies
    # =========================================================================
    # Drop FK constraint on account_id first
    op.drop_constraint("strategies_account_id_fkey", "strategies", type_="foreignkey")
    # Drop old columns that moved to agents
    op.drop_column("strategies", "account_id")
    op.drop_column("strategies", "ai_model")
    op.drop_column("strategies", "prompt")
    op.drop_column("strategies", "trading_mode")
    op.drop_column("strategies", "allocated_capital")
    op.drop_column("strategies", "allocated_capital_percent")
    op.drop_column("strategies", "status")
    op.drop_column("strategies", "error_message")
    op.drop_column("strategies", "total_pnl")
    op.drop_column("strategies", "total_trades")
    op.drop_column("strategies", "winning_trades")
    op.drop_column("strategies", "losing_trades")
    op.drop_column("strategies", "max_drawdown")
    op.drop_column("strategies", "last_run_at")
    op.drop_column("strategies", "next_run_at")

    # Drop old strategy_id FK and column from decision_records
    op.drop_constraint("decision_records_strategy_id_fkey", "decision_records", type_="foreignkey")
    op.drop_index("ix_decision_records_strategy_id", "decision_records")
    op.drop_column("decision_records", "strategy_id")

    # =========================================================================
    # Step 10: Drop old tables
    # =========================================================================
    op.drop_table("strategy_positions")
    op.drop_table("quant_strategies")


def downgrade() -> None:
    """Reverse the Strategy/Agent decoupling migration.

    WARNING: This is a lossy downgrade. Data from quant strategies
    merged into the strategies table will be lost. Only use in development.
    """
    # This is a complex migration - downgrade is best-effort for dev use
    raise NotImplementedError(
        "Downgrade of strategy/agent decoupling is not supported. "
        "Restore from backup instead."
    )
