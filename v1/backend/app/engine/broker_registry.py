"""Process-wide singleton: which BrokerAdapter is currently wired in.

v1 Phase 1: defaults to the in-process PaperBroker so the system works
without Alpaca keys. Swap to AlpacaPaperBroker once .env is filled in.
"""
from __future__ import annotations

from decimal import Decimal

from app.brokers.base import BrokerAdapter
from app.brokers.paper import PaperBroker

# Dev convenience: seed a few starter quotes so paper market orders fill
# immediately when the UI is opened the first time. Real data wiring (Alpaca
# stream → bus → broker) replaces this in phase 1.5.
_DEV_QUOTES: dict[str, Decimal] = {
    "AAPL": Decimal("220.50"),
    "MSFT": Decimal("420.00"),
    "NVDA": Decimal("135.00"),
    "SPY": Decimal("560.00"),
}

_broker: BrokerAdapter | None = None
_kill_switch: bool = False


def get_broker() -> BrokerAdapter:
    global _broker
    if _broker is None:
        b = PaperBroker()
        for sym, px in _DEV_QUOTES.items():
            b.set_last_price(sym, px)
        _broker = b
    return _broker


def set_broker(b: BrokerAdapter) -> None:
    global _broker
    _broker = b


def kill_switch_engaged() -> bool:
    return _kill_switch


def engage_kill_switch() -> None:
    global _kill_switch
    _kill_switch = True


def reset_kill_switch() -> None:
    global _kill_switch
    _kill_switch = False
