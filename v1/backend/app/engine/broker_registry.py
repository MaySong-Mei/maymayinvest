"""Process-wide singleton: which BrokerAdapter is currently wired in.

v1 Phase 1: defaults to the in-process PaperBroker so the system works
without Alpaca keys. Swap to AlpacaPaperBroker once .env is filled in.
"""
from __future__ import annotations

from app.brokers.base import BrokerAdapter
from app.brokers.paper import PaperBroker

_broker: BrokerAdapter | None = None
_kill_switch: bool = False


def get_broker() -> BrokerAdapter:
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
