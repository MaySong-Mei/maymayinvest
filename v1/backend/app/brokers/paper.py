"""In-process deterministic paper broker.

Useful for tests and for running a strategy without any network round-trip.
Fills market orders immediately at a quote provided externally; limit orders
fill if price crosses.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from app.core.time import utcnow
from app.domain.order import Fill, Order, OrderIntent, OrderState, OrderType
from app.domain.position import Portfolio, Position


class PaperBroker:
    name = "paper"

    def __init__(self, account_id: str = "paper-default", starting_cash: Decimal = Decimal("100000")) -> None:
        self.account_id = account_id
        self._cash = starting_cash
        self._orders: dict[UUID, Order] = {}
        self._fills: list[Fill] = []
        self._positions: dict[str, Decimal] = {}
        self._avg_cost: dict[str, Decimal] = {}
        self._last_price: dict[str, Decimal] = {}

    async def connect(self) -> None:
        return None

    def set_last_price(self, symbol: str, price: Decimal) -> None:
        self._last_price[symbol] = Decimal(price)

    async def get_last_price(self, symbol: str) -> Decimal:
        if symbol not in self._last_price:
            raise LookupError(f"no quote set for {symbol}")
        return self._last_price[symbol]

    async def submit_order(self, intent: OrderIntent) -> Order:
        # Idempotency: identical client_order_id returns existing order.
        if intent.client_order_id in self._orders:
            return self._orders[intent.client_order_id]

        order = Order(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            qty=intent.qty,
            type=intent.type,
            limit_price=intent.limit_price,
            tif=intent.tif,
            state=OrderState.SUBMITTED,
            submitted_at=utcnow(),
            strategy_id=intent.strategy_id,
            sub_portfolio_id=intent.sub_portfolio_id,
        )
        self._orders[intent.client_order_id] = order

        price = self._last_price.get(intent.symbol)
        fill_price: Decimal | None = None
        if intent.type == OrderType.MARKET and price is not None:
            fill_price = price
        elif intent.type == OrderType.LIMIT and price is not None and intent.limit_price is not None:
            if (intent.side == "buy" and price <= intent.limit_price) or (
                intent.side == "sell" and price >= intent.limit_price
            ):
                fill_price = intent.limit_price

        if fill_price is not None:
            self._apply_fill(order, fill_price)
        else:
            order.state = OrderState.ACK
            order.acked_at = utcnow()

        return order

    def _apply_fill(self, order: Order, price: Decimal) -> None:
        signed_qty = order.qty if order.side == "buy" else -order.qty
        cur = self._positions.get(order.symbol, Decimal("0"))
        new_qty = cur + signed_qty

        if order.side == "buy":
            self._cash -= order.qty * price
            prev_cost = self._avg_cost.get(order.symbol, Decimal("0"))
            total = (cur * prev_cost) + (order.qty * price)
            self._avg_cost[order.symbol] = (total / new_qty) if new_qty != 0 else Decimal("0")
        else:
            self._cash += order.qty * price
            if new_qty == 0:
                self._avg_cost.pop(order.symbol, None)

        self._positions[order.symbol] = new_qty
        order.state = OrderState.FILLED
        order.acked_at = utcnow()
        order.closed_at = utcnow()

        self._fills.append(
            Fill(
                fill_id=str(uuid4()),
                client_order_id=order.client_order_id,
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                price=price,
                ts=utcnow(),
                sub_portfolio_id=order.sub_portfolio_id,
                strategy_id=order.strategy_id,
            )
        )

    async def cancel_order(self, client_order_id: UUID) -> None:
        order = self._orders.get(client_order_id)
        if order and order.state in (OrderState.SUBMITTED, OrderState.ACK, OrderState.PARTIAL):
            order.state = OrderState.CANCELED
            order.closed_at = utcnow()

    async def list_open_orders(self) -> list[Order]:
        return [
            o
            for o in self._orders.values()
            if o.state in (OrderState.SUBMITTED, OrderState.ACK, OrderState.PARTIAL)
        ]

    async def list_fills_since(self, ts) -> list[Fill]:
        return [f for f in self._fills if f.ts >= ts]

    async def get_portfolio(self) -> Portfolio:
        positions = [
            Position(symbol=s, qty=q, avg_cost=self._avg_cost.get(s, Decimal("0")))
            for s, q in self._positions.items()
            if q != 0
        ]
        equity = self._cash + sum(
            (p.qty * self._last_price.get(p.symbol, p.avg_cost) for p in positions),
            Decimal("0"),
        )
        return Portfolio(
            account_id=self.account_id,
            cash=self._cash,
            positions=positions,
            equity=equity,
        )
