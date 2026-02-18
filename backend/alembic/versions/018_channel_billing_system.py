"""Add channel invitation and billing system

Adds tables for channel management, user wallets, and billing:
- channels: Channel/distributor management
- wallets: User wallet balances
- channel_wallets: Channel commission wallets
- wallet_transactions: User transaction history
- channel_transactions: Channel transaction history
- recharge_orders: Recharge order records

Also extends users table with invite_code, referrer_id, channel_id, role fields.

Revision ID: 018
Revises: 017
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # 1. Extend users table with invitation and role fields
    # ==========================================================================
    op.add_column("users", sa.Column("invite_code", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("referrer_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))

    # Create unique constraint for invite_code
    op.create_unique_constraint("uq_users_invite_code", "users", ["invite_code"])

    # Create foreign keys for users table
    op.create_foreign_key(
        "fk_users_referrer_id",
        "users", "users",
        ["referrer_id"], ["id"],
        ondelete="SET NULL"
    )

    # Create indexes for users table
    op.create_index("ix_users_invite_code", "users", ["invite_code"])
    op.create_index("ix_users_referrer_id", "users", ["referrer_id"])
    op.create_index("ix_users_channel_id", "users", ["channel_id"])
    op.create_index("ix_users_role", "users", ["role"])

    # ==========================================================================
    # 2. Create channels table
    # ==========================================================================
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        # Basic info
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Commission settings
        sa.Column("commission_rate", sa.Float, nullable=False, server_default="0.0"),
        # Status
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        # Contact info
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        # Statistics (denormalized for performance)
        sa.Column("total_users", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_revenue", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_commission", sa.Float, nullable=False, server_default="0.0"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        # Constraints
        sa.UniqueConstraint("code", name="uq_channels_code"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_channels_code", "channels", ["code"])
    op.create_index("ix_channels_status", "channels", ["status"])
    op.create_index("ix_channels_admin_user_id", "channels", ["admin_user_id"])

    # Now add the channel foreign key to users (after channels table exists)
    op.create_foreign_key(
        "fk_users_channel_id",
        "users", "channels",
        ["channel_id"], ["id"],
        ondelete="SET NULL"
    )

    # ==========================================================================
    # 3. Create wallets table (user wallets)
    # ==========================================================================
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Balance
        sa.Column("balance", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("frozen_balance", sa.Float, nullable=False, server_default="0.0"),
        # Statistics
        sa.Column("total_recharged", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_consumed", sa.Float, nullable=False, server_default="0.0"),
        # Optimistic locking
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        # Constraints
        sa.UniqueConstraint("user_id", name="uq_wallets_user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])

    # ==========================================================================
    # 4. Create channel_wallets table
    # ==========================================================================
    op.create_table(
        "channel_wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Balance
        sa.Column("balance", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("frozen_balance", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("pending_commission", sa.Float, nullable=False, server_default="0.0"),
        # Statistics
        sa.Column("total_commission", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_withdrawn", sa.Float, nullable=False, server_default="0.0"),
        # Optimistic locking
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        # Constraints
        sa.UniqueConstraint("channel_id", name="uq_channel_wallets_channel_id"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_channel_wallets_channel_id", "channel_wallets", ["channel_id"])

    # ==========================================================================
    # 5. Create wallet_transactions table (user transaction history)
    # ==========================================================================
    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Transaction type: recharge/consume/refund/gift/adjustment
        sa.Column("type", sa.String(30), nullable=False),
        # Amount and balance snapshot
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("balance_before", sa.Float, nullable=False),
        sa.Column("balance_after", sa.Float, nullable=False),
        # Reference info
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Commission info (JSON: {channel_id, channel_amount, platform_amount})
        sa.Column("commission_info", postgresql.JSON(), nullable=True),
        # Description
        sa.Column("description", sa.Text, nullable=True),
        # Timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        # Constraints
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])
    op.create_index("ix_wallet_transactions_user_id", "wallet_transactions", ["user_id"])
    op.create_index("ix_wallet_transactions_type", "wallet_transactions", ["type"])
    op.create_index("ix_wallet_transactions_created_at", "wallet_transactions", ["created_at"])
    op.create_index("ix_wallet_transactions_reference", "wallet_transactions",
                    ["reference_type", "reference_id"])

    # ==========================================================================
    # 6. Create channel_transactions table
    # ==========================================================================
    op.create_table(
        "channel_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Transaction type: commission/withdraw/adjustment/refund
        sa.Column("type", sa.String(30), nullable=False),
        # Amount and balance snapshot
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("balance_before", sa.Float, nullable=False),
        sa.Column("balance_after", sa.Float, nullable=False),
        # Reference info
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Description
        sa.Column("description", sa.Text, nullable=True),
        # Timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        # Constraints
        sa.ForeignKeyConstraint(["wallet_id"], ["channel_wallets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_channel_transactions_wallet_id", "channel_transactions", ["wallet_id"])
    op.create_index("ix_channel_transactions_channel_id", "channel_transactions", ["channel_id"])
    op.create_index("ix_channel_transactions_source_user_id", "channel_transactions", ["source_user_id"])
    op.create_index("ix_channel_transactions_type", "channel_transactions", ["type"])
    op.create_index("ix_channel_transactions_created_at", "channel_transactions", ["created_at"])

    # ==========================================================================
    # 7. Create recharge_orders table
    # ==========================================================================
    op.create_table(
        "recharge_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Order info
        sa.Column("order_no", sa.String(50), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("bonus_amount", sa.Float, nullable=False, server_default="0.0"),
        # Payment
        sa.Column("payment_method", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        # Timestamps
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
        # Note
        sa.Column("note", sa.Text, nullable=True),
        # Constraints
        sa.UniqueConstraint("order_no", name="uq_recharge_orders_order_no"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_recharge_orders_user_id", "recharge_orders", ["user_id"])
    op.create_index("ix_recharge_orders_order_no", "recharge_orders", ["order_no"])
    op.create_index("ix_recharge_orders_status", "recharge_orders", ["status"])
    op.create_index("ix_recharge_orders_created_at", "recharge_orders", ["created_at"])


def downgrade() -> None:
    # Drop recharge_orders
    op.drop_index("ix_recharge_orders_created_at")
    op.drop_index("ix_recharge_orders_status")
    op.drop_index("ix_recharge_orders_order_no")
    op.drop_index("ix_recharge_orders_user_id")
    op.drop_table("recharge_orders")

    # Drop channel_transactions
    op.drop_index("ix_channel_transactions_created_at")
    op.drop_index("ix_channel_transactions_type")
    op.drop_index("ix_channel_transactions_source_user_id")
    op.drop_index("ix_channel_transactions_channel_id")
    op.drop_index("ix_channel_transactions_wallet_id")
    op.drop_table("channel_transactions")

    # Drop wallet_transactions
    op.drop_index("ix_wallet_transactions_reference")
    op.drop_index("ix_wallet_transactions_created_at")
    op.drop_index("ix_wallet_transactions_type")
    op.drop_index("ix_wallet_transactions_user_id")
    op.drop_index("ix_wallet_transactions_wallet_id")
    op.drop_table("wallet_transactions")

    # Drop channel_wallets
    op.drop_index("ix_channel_wallets_channel_id")
    op.drop_table("channel_wallets")

    # Drop wallets
    op.drop_index("ix_wallets_user_id")
    op.drop_table("wallets")

    # Drop channels (first drop fk from users)
    op.drop_constraint("fk_users_channel_id", "users", type_="foreignkey")
    op.drop_index("ix_channels_admin_user_id")
    op.drop_index("ix_channels_status")
    op.drop_index("ix_channels_code")
    op.drop_table("channels")

    # Drop users table extensions
    op.drop_index("ix_users_role")
    op.drop_index("ix_users_channel_id")
    op.drop_index("ix_users_referrer_id")
    op.drop_index("ix_users_invite_code")
    op.drop_constraint("fk_users_referrer_id", "users", type_="foreignkey")
    op.drop_constraint("uq_users_invite_code", "users", type_="unique")
    op.drop_column("users", "role")
    op.drop_column("users", "channel_id")
    op.drop_column("users", "referrer_id")
    op.drop_column("users", "invite_code")
