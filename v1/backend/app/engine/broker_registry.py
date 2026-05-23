"""Process-wide singleton: which BrokerAdapter is currently wired in.

v1 Phase 1: defaults to the in-process PaperBroker so the system works
without Alpaca keys. Swap to AlpacaPaperBroker once .env is filled in.

Note on price seeding (removed 2026-05-23): previously this module
seeded a few starter quotes (AAPL 220.50, MSFT 420.00, etc) on first
get_broker() call. That convenience leaked stale prices into a real
event-driven test on 2024-05-02 data, where the analyzer noted the
price was inconsistent with the event timestamp but still sized
against it. The dev seed was dev infra leaking into production-shaped
runs; it has been removed.

If your test or script needs a price, set it explicitly via
broker.set_last_price(symbol, price) after constructing or fetching
the broker. This makes "where did this price come from" auditable
in every test that uses the paper broker.
"""
from __future__ import annotations

from app.brokers.base import BrokerAdapter
from app.brokers.paper import PaperBroker

_broker: BrokerAdapter | None = None
_kill_switch: bool = False


def get_broker() -> BrokerAdapter:
    """Return the process-wide BrokerAdapter singleton.

    Lazy-initialized to an empty PaperBroker. The broker has no
    starter quotes; callers must explicitly seed prices for any
    symbols they trade. This is deliberate — implicit dev seeds
    have leaked into production-shaped tests before.
    """
    global _broker
    if _broker is None:
        _broker = PaperBroker()
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
