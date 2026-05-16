"""BrokerAdapter protocol — every broker implements this.

Invariants every adapter MUST uphold:
  - round-trip client_order_id (broker should dedupe on resubmit)
  - return Order with state transitions (pending_local → submitted → ack → filled|canceled)
  - never raise on duplicate client_order_id; return the existing Order instead
"""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.domain.order import Fill, Order, OrderIntent
from app.domain.position import Portfolio


class BrokerAdapter(Protocol):
    name: str
    account_id: str

    async def connect(self) -> None: ...
    async def submit_order(self, intent: OrderIntent) -> Order: ...
    async def cancel_order(self, client_order_id: UUID) -> None: ...
    async def list_open_orders(self) -> list[Order]: ...
    async def list_fills_since(self, ts) -> list[Fill]: ...
    async def get_portfolio(self) -> Portfolio: ...
    async def get_last_price(self, symbol: str) -> Decimal: ...
