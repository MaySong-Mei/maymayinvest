"""Invariant: agent invocations of `act` capabilities default to dry-run.

Uses a stub OperatorContext with an in-memory session that captures audit
inserts so we don't need Postgres in the unit suite.
"""
import asyncio
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest

from app.domain.order import OrderIntent, OrderSide
from app.operator.context import OperatorContext
from app.operator.registry import capability, registry


class _FakeSession:
    def __init__(self):
        self.inserts: list[Any] = []

    async def execute(self, stmt):
        self.inserts.append(stmt)
        return None


@dataclass
class _CapturedCalls:
    real_calls: int = 0


@pytest.fixture()
def caps():
    captured = _CapturedCalls()
    unique = f"test_submit_order_{uuid.uuid4().hex[:8]}"

    @capability(
        name=unique,
        category="act",
        max_calls_per_minute=10,
        requires_reasoning_for=("agent",),
        dry_run_default_for=("agent",),
    )
    async def _submit(ctx: OperatorContext, intent: OrderIntent):
        captured.real_calls += 1
        return {"executed": True, "client_order_id": str(intent.client_order_id)}

    yield _submit, captured
    registry.capabilities.pop(unique, None)


def test_agent_call_without_execute_is_dry_run(caps):
    func, captured = caps

    async def run():
        ctx = OperatorContext(
            actor_id="claude",
            actor_type="agent",
            session=_FakeSession(),
            reasoning="testing dry-run gate",
        )
        intent = OrderIntent(symbol="AAPL", side=OrderSide.BUY, qty=Decimal("1"))
        result = await func(ctx, intent)
        assert result["dry_run"] is True
        assert captured.real_calls == 0

    asyncio.run(run())


def test_agent_call_with_execute_true_runs(caps):
    func, captured = caps

    async def run():
        ctx = OperatorContext(
            actor_id="claude",
            actor_type="agent",
            session=_FakeSession(),
            reasoning="confirmed execute",
        )
        intent = OrderIntent(symbol="AAPL", side=OrderSide.BUY, qty=Decimal("1"))
        result = await func(ctx, intent, execute=True)
        assert result["executed"] is True
        assert captured.real_calls == 1

    asyncio.run(run())


def test_user_call_runs_immediately(caps):
    func, captured = caps

    async def run():
        ctx = OperatorContext(
            actor_id="me",
            actor_type="user",
            session=_FakeSession(),
        )
        intent = OrderIntent(symbol="AAPL", side=OrderSide.BUY, qty=Decimal("1"))
        result = await func(ctx, intent)
        assert result["executed"] is True
        assert captured.real_calls == 1

    asyncio.run(run())
