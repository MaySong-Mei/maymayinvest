"""SQLAlchemy ORM. Invariants enforced at schema level:

- All monetary fields = Numeric(20, 8)
- All timestamps = TIMESTAMPTZ
- `fills` is authoritative; `tax_lots` rolls forward from fills
- `actions` is append-only audit
- `bars_1d` is a TimescaleDB hypertable (created via migration after table creation)
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import JSON, BigInteger, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

MONEY = Numeric(20, 8)


class Base(DeclarativeBase):
    pass


class Instrument(Base):
    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(16))
    asset_class: Mapped[str] = mapped_column(String(16))
    currency: Mapped[str] = mapped_column(String(3))
    calendar_id: Mapped[str] = mapped_column(String(32), default="XNYS")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    broker: Mapped[str] = mapped_column(String(32))  # "alpaca_paper", "paper", "alpaca_live"
    scope: Mapped[str] = mapped_column(String(16), default="paper")  # "paper" | "live"
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")


class Order(Base):
    __tablename__ = "orders"

    client_order_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8))
    qty: Mapped[Decimal] = mapped_column(MONEY)
    type: Mapped[str] = mapped_column(String(16))
    limit_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    tif: Mapped[str] = mapped_column(String(8), default="day")
    state: Mapped[str] = mapped_column(String(16), default="pending_local")
    submitted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    acked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sub_portfolio_id: Mapped[str] = mapped_column(String(64), default="default")
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)


class Fill(Base):
    __tablename__ = "fills"

    fill_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.client_order_id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8))
    qty: Mapped[Decimal] = mapped_column(MONEY)
    price: Mapped[Decimal] = mapped_column(MONEY)
    fee: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    sub_portfolio_id: Mapped[str] = mapped_column(String(64), default="default")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TaxLot(Base):
    """One row per acquisition that still has remaining qty. FIFO consumed on sells."""

    __tablename__ = "tax_lots"

    lot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(String(32))
    sub_portfolio_id: Mapped[str] = mapped_column(String(64), default="default")
    acquired_at_fill_id: Mapped[str] = mapped_column(ForeignKey("fills.fill_id"))
    qty_open: Mapped[Decimal] = mapped_column(MONEY)
    cost_basis: Mapped[Decimal] = mapped_column(MONEY)  # per-unit incl. fee allocation
    opened_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32))
    ex_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    kind: Mapped[str] = mapped_column(String(16))  # "split" | "dividend" | "spinoff"
    payload: Mapped[dict] = mapped_column(JSON)  # ratio, cash, etc

    __table_args__ = (UniqueConstraint("symbol", "ex_date", "kind", name="ux_ca_sym_date_kind"),)


class Action(Base):
    """Append-only audit log for every operator capability invocation."""

    __tablename__ = "actions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_id: Mapped[str] = mapped_column(String(64))
    actor_type: Mapped[str] = mapped_column(String(16))  # "user" | "agent"
    capability: Mapped[str] = mapped_column(String(64))
    intent: Mapped[dict] = mapped_column(JSON)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_status: Mapped[str] = mapped_column(String(16))  # "ok" | "dry_run" | "denied" | "error"
    outcome: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))


class Bar1d(Base):
    """Daily bars — converted to TimescaleDB hypertable in migration."""

    __tablename__ = "bars_1d"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(MONEY)
    high: Mapped[Decimal] = mapped_column(MONEY)
    low: Mapped[Decimal] = mapped_column(MONEY)
    close: Mapped[Decimal] = mapped_column(MONEY)
    volume: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
