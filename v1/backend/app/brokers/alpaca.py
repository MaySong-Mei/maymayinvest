"""Alpaca paper-trading adapter.

Lazy-imports alpaca-py so the rest of the app can run without keys configured.
Maps Alpaca's order states into our OrderState enum and round-trips
client_order_id (Alpaca's `client_order_id` field is dedup'd by the broker).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.time import utcnow
from app.domain.order import Fill, Order, OrderIntent, OrderSide, OrderState, OrderType, TimeInForce
from app.domain.position import Portfolio, Position

_STATE_MAP = {
    "new": OrderState.ACK,
    "accepted": OrderState.ACK,
    "pending_new": OrderState.SUBMITTED,
    "partially_filled": OrderState.PARTIAL,
    "filled": OrderState.FILLED,
    "canceled": OrderState.CANCELED,
    "expired": OrderState.CANCELED,
    "rejected": OrderState.REJECTED,
}


class AlpacaPaperBroker:
    name = "alpaca_paper"

    def __init__(self, account_id: str = "alpaca-paper") -> None:
        self.account_id = account_id
        self._trading: Any = None
        self._data: Any = None

    async def connect(self) -> None:
        # Lazy import: keeps test envs without alpaca-py installed working.
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.trading.client import TradingClient

        s = get_settings()
        self._trading = TradingClient(
            api_key=s.alpaca_api_key.get_secret_value(),
            secret_key=s.alpaca_api_secret.get_secret_value(),
            paper=True,
        )
        self._data = StockHistoricalDataClient(
            api_key=s.alpaca_api_key.get_secret_value(),
            secret_key=s.alpaca_api_secret.get_secret_value(),
        )

    async def submit_order(self, intent: OrderIntent) -> Order:
        from alpaca.trading.enums import OrderSide as AS
        from alpaca.trading.enums import TimeInForce as AT_TIF
        from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

        assert self._trading is not None, "call connect() first"
        side = AS.BUY if intent.side == OrderSide.BUY else AS.SELL
        tif_map = {TimeInForce.DAY: AT_TIF.DAY, TimeInForce.GTC: AT_TIF.GTC, TimeInForce.IOC: AT_TIF.IOC}
        tif = tif_map[intent.tif]

        if intent.type == OrderType.MARKET:
            req = MarketOrderRequest(
                symbol=intent.symbol,
                qty=float(intent.qty),
                side=side,
                time_in_force=tif,
                client_order_id=str(intent.client_order_id),
            )
        else:
            if intent.limit_price is None:
                raise ValueError("limit order requires limit_price")
            req = LimitOrderRequest(
                symbol=intent.symbol,
                qty=float(intent.qty),
                side=side,
                time_in_force=tif,
                limit_price=float(intent.limit_price),
                client_order_id=str(intent.client_order_id),
            )

        # Alpaca dedupes on client_order_id and returns the original order on duplicate.
        ao = self._trading.submit_order(req)
        return self._to_domain(ao, intent)

    def _to_domain(self, ao: Any, intent: OrderIntent | None) -> Order:
        return Order(
            client_order_id=UUID(ao.client_order_id) if ao.client_order_id else (intent.client_order_id if intent else UUID(int=0)),
            broker_order_id=str(ao.id),
            symbol=ao.symbol,
            side=OrderSide(ao.side.value.lower()),
            qty=Decimal(str(ao.qty)),
            type=OrderType(ao.order_type.value.lower()) if hasattr(ao, "order_type") else OrderType.MARKET,
            limit_price=Decimal(str(ao.limit_price)) if ao.limit_price else None,
            tif=TimeInForce(ao.time_in_force.value.lower()) if hasattr(ao, "time_in_force") else TimeInForce.DAY,
            state=_STATE_MAP.get(ao.status.value.lower(), OrderState.SUBMITTED),
            submitted_at=ao.submitted_at or utcnow(),
            acked_at=ao.updated_at,
            closed_at=ao.filled_at or ao.canceled_at,
        )

    async def cancel_order(self, client_order_id: UUID) -> None:
        assert self._trading is not None, "call connect() first"
        ao = self._trading.get_order_by_client_id(str(client_order_id))
        self._trading.cancel_order_by_id(ao.id)

    async def list_open_orders(self) -> list[Order]:
        from alpaca.trading.enums import QueryOrderStatus
        from alpaca.trading.requests import GetOrdersRequest

        assert self._trading is not None, "call connect() first"
        req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        return [self._to_domain(a, None) for a in self._trading.get_orders(req)]

    async def list_fills_since(self, ts: datetime) -> list[Fill]:
        # Alpaca exposes fills via activities API; covered in phase 1 only if needed for reconciliation.
        # For now return empty — the paper broker covers the test path.
        return []

    async def get_portfolio(self) -> Portfolio:
        assert self._trading is not None, "call connect() first"
        acct = self._trading.get_account()
        raw_positions = self._trading.get_all_positions()
        positions = [
            Position(
                symbol=p.symbol,
                qty=Decimal(str(p.qty)),
                avg_cost=Decimal(str(p.avg_entry_price)),
            )
            for p in raw_positions
        ]
        return Portfolio(
            account_id=self.account_id,
            base_currency=acct.currency or "USD",
            cash=Decimal(str(acct.cash)),
            positions=positions,
            equity=Decimal(str(acct.equity)),
        )

    async def get_last_price(self, symbol: str) -> Decimal:
        from alpaca.data.requests import StockLatestTradeRequest

        assert self._data is not None, "call connect() first"
        req = StockLatestTradeRequest(symbol_or_symbols=symbol, feed=get_settings().alpaca_data_feed)
        result = self._data.get_stock_latest_trade(req)
        trade = result[symbol]
        return Decimal(str(trade.price))


_ = timezone  # keep import-cleanup from removing tz import (used in subclasses later)
