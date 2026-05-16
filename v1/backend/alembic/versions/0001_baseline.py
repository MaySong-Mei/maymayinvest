"""Baseline schema.

- All money columns are Numeric(20,8); all timestamps are TIMESTAMPTZ.
- fills is the authoritative ledger; tax_lots roll forward from fills.
- actions is the append-only audit log shared by users and agents.
- bars_1d is converted to a TimescaleDB hypertable at the end.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY = sa.Numeric(20, 8)


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("symbol", sa.String(32), primary_key=True),
        sa.Column("exchange", sa.String(16), nullable=False),
        sa.Column("asset_class", sa.String(16), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("calendar_id", sa.String(32), nullable=False, server_default="XNYS"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("broker", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False, server_default="paper"),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
    )

    op.create_table(
        "orders",
        sa.Column("client_order_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("broker_order_id", sa.String(64), unique=True, nullable=True),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("qty", MONEY, nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("limit_price", MONEY, nullable=True),
        sa.Column("tif", sa.String(8), nullable=False, server_default="day"),
        sa.Column("state", sa.String(16), nullable=False, server_default="pending_local"),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("acked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("strategy_id", sa.String(64), nullable=True),
        sa.Column("sub_portfolio_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column("reasoning", sa.Text, nullable=True),
    )
    op.create_index("ix_orders_symbol_state", "orders", ["symbol", "state"])
    op.create_index("ix_orders_strategy", "orders", ["strategy_id"])

    op.create_table(
        "fills",
        sa.Column("fill_id", sa.String(64), primary_key=True),
        sa.Column(
            "client_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.client_order_id"),
            nullable=False,
        ),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("qty", MONEY, nullable=False),
        sa.Column("price", MONEY, nullable=False),
        sa.Column("fee", MONEY, nullable=False, server_default="0"),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sub_portfolio_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column("strategy_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_fills_symbol_ts", "fills", ["symbol", "ts"])
    op.create_index("ix_fills_account_ts", "fills", ["account_id", "ts"])

    op.create_table(
        "tax_lots",
        sa.Column("lot_id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("sub_portfolio_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column(
            "acquired_at_fill_id",
            sa.String(64),
            sa.ForeignKey("fills.fill_id"),
            nullable=False,
        ),
        sa.Column("qty_open", MONEY, nullable=False),
        sa.Column("cost_basis", MONEY, nullable=False),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_taxlots_open", "tax_lots", ["account_id", "symbol", "closed_at"])

    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("ex_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.UniqueConstraint("symbol", "ex_date", "kind", name="ux_ca_sym_date_kind"),
    )

    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("capability", sa.String(64), nullable=False),
        sa.Column("intent", sa.JSON, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("outcome_status", sa.String(16), nullable=False),
        sa.Column("outcome", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_actions_actor_ts", "actions", ["actor_id", "ts"])
    op.create_index("ix_actions_capability_ts", "actions", ["capability", "ts"])

    op.create_table(
        "bars_1d",
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("open", MONEY, nullable=False),
        sa.Column("high", MONEY, nullable=False),
        sa.Column("low", MONEY, nullable=False),
        sa.Column("close", MONEY, nullable=False),
        sa.Column("volume", MONEY, nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("symbol", "ts"),
    )
    # Convert bars_1d to a TimescaleDB hypertable (Postgres+Timescale only).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "SELECT create_hypertable('bars_1d', 'ts', if_not_exists => TRUE, migrate_data => TRUE);"
        )


def downgrade() -> None:
    op.drop_table("bars_1d")
    op.drop_index("ix_actions_capability_ts", table_name="actions")
    op.drop_index("ix_actions_actor_ts", table_name="actions")
    op.drop_table("actions")
    op.drop_table("corporate_actions")
    op.drop_index("ix_taxlots_open", table_name="tax_lots")
    op.drop_table("tax_lots")
    op.drop_index("ix_fills_account_ts", table_name="fills")
    op.drop_index("ix_fills_symbol_ts", table_name="fills")
    op.drop_table("fills")
    op.drop_index("ix_orders_strategy", table_name="orders")
    op.drop_index("ix_orders_symbol_state", table_name="orders")
    op.drop_table("orders")
    op.drop_table("accounts")
    op.drop_table("instruments")
