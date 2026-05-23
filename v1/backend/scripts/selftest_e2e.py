"""End-to-end selftest: event -> dossier -> route -> promote -> broker fill -> audit.

This is the FIRST runnable demonstration of the full pipeline. Each component
has unit tests; this script exercises the glue between them in order to prove
the loop actually runs.

Pipeline:
  1. Synthesize an Event (kind=TEST_SYNTHETIC) — bypasses the missing real
     EDGAR poller. The fact that the analyzer doesn't care where the event
     came from is part of the layering invariant.
  2. Persist via save_event (idempotent).
  3. Run StubAnalyzer to produce a DecisionDossier. StubAnalyzer always
     returns mode="notify" with no intent, so we manually override the
     dossier here to mode="dry_run" + a real intent — this simulates what
     a real analyzer would do for an actionable event.
  4. Route the dossier via route_decision (dry_run path persists + enqueues).
  5. Inspect pending_signals: one row should exist, status='pending'.
  6. Call the promote_signal capability via the operator surface. This is
     the user action that turns a dry-run proposal into a real submission.
  7. Inspect broker: position should now exist; original intent
     client_order_id should appear in orders.
  8. Inspect pending_signals row: status should be 'promoted',
     resulting_client_order_id linked.
  9. Inspect actions table: there should be at least
     - one row for promote_signal (outcome ok)
     - one row for submit_order (outcome ok) — submitted by the capability
       chain from inside promote_signal
       NOTE: as of writing, promote_signal calls broker.submit_order
       directly rather than going through the submit_order capability.
       This is intentional — promote_signal's audit row IS the audit for
       this whole action, and adding a nested submit_order audit would
       double-count. The test asserts this design.

Auth requirements:
  None — this selftest uses StubAnalyzer (no LLM) and the in-process
  PaperBroker. No CLAUDE_CODE_OAUTH_TOKEN needed.

Database:
  Uses in-memory aiosqlite, builds the schema via Base.metadata.create_all
  (matches the pattern in scripts/selftest_api.py).
"""
from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Make backend importable when run from any cwd
_REPO_BACKEND = Path(__file__).resolve().parent.parent
if str(_REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(_REPO_BACKEND))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.brokers.paper import PaperBroker
from app.domain.decision import ProposedOrder
from app.domain.event import Event, EventKind
from app.domain.order import OrderIntent, OrderSide, OrderState, OrderType
from app.engine.broker_registry import reset_kill_switch, set_broker
from app.intel.adapters import OperatorOrderSubmitter
from app.intel.analyzer.base import AnalyzerContext
from app.intel.analyzer.stub import StubAnalyzer
from app.intel.router import RouterContext, route_decision
from app.operator.capabilities import PromoteSignalReq, promote_signal
from app.operator.context import OperatorContext
from app.persistence.models import Action, Base, Decision, PendingSignal
from app.persistence.repositories.events import save_event


def _hr(title: str) -> None:
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


async def main() -> int:
    # ---------- bootstrap ----------
    _hr("0. bootstrap (in-memory sqlite + fresh PaperBroker)")

    pb = PaperBroker()
    pb.set_last_price("AAPL", Decimal("220.50"))
    set_broker(pb)
    reset_kill_switch()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        # ---------- 1. synthesize event ----------
        _hr("1. synthesize Event (kind=test_synthetic, AAPL)")

        event = Event(
            kind=EventKind.TEST_SYNTHETIC,
            external_id="selftest-e2e:001",
            ts=datetime(2026, 5, 22, 14, 30, tzinfo=UTC),
            source="selftest",
            symbols=["AAPL"],
            headline="Apple announces $90B buyback (synthetic event for e2e selftest)",
            payload={"accession": "selftest-001"},
        )
        await save_event(session, event)
        print(f"  event saved: id={event.id}, external_id={event.external_id}")

        # ---------- 2-3. analyze ----------
        _hr("2. StubAnalyzer produces DecisionDossier")

        analyzer = StubAnalyzer()
        ctx = AnalyzerContext(actor_id="selftest-stub-analyzer")
        dossier = await analyzer.analyze(event, ctx)

        # StubAnalyzer's default dossier has mode='notify' and no intent.
        # Simulate a real analyzer's actionable output by overriding:
        intent = OrderIntent(
            symbol="AAPL",
            side=OrderSide.BUY,
            qty=Decimal("5"),
            type=OrderType.MARKET,
        )
        object.__setattr__(dossier, "mode", "dry_run")
        object.__setattr__(dossier, "proposed", ProposedOrder(intent=intent))
        # Note: the stub's reasoning_chain is preserved; downstream consumers
        # see it. A real analyzer would write its own reasoning here.

        print(f"  dossier produced: id={dossier.id}, mode={dossier.mode}")
        print(f"    proposed intent: {intent.symbol} {intent.side.value} {intent.qty}")

        # ---------- 4. route ----------
        _hr("3. route_decision (dry_run -> pending_signal enqueued)")

        submitter = OperatorOrderSubmitter(session=session, actor_id="auto-router")
        rctx = RouterContext(session=session, submitter=submitter, actor_id="selftest")
        result = await route_decision(rctx, dossier)
        print(f"  route result: {result}")
        assert result.mode == "dry_run"
        assert result.pending_signal_id is not None
        assert result.order is None, "dry_run must not call broker"

        # ---------- 5. inspect pending ----------
        _hr("4. inspect pending_signals (should be 1 row, status=pending)")

        pending_rows = (await session.execute(select(PendingSignal))).scalars().all()
        for row in pending_rows:
            print(
                f"  pending: id={row.id}, dossier_id={row.dossier_id}, "
                f"mode={row.mode}, status={row.status}"
            )
        assert len(pending_rows) == 1
        assert pending_rows[0].status == "pending"
        signal_id = pending_rows[0].id

        # ---------- 6. promote ----------
        _hr("5. promote_signal capability (user-initiated)")

        op_ctx = OperatorContext(
            actor_id="me",
            actor_type="user",
            session=session,
            reasoning="e2e selftest: manual promotion of pending dry-run signal",
        )
        order = await promote_signal(op_ctx, PromoteSignalReq(pending_signal_id=signal_id))
        print(f"  order returned: client_order_id={order.client_order_id}")
        print(f"    state={order.state.value}, symbol={order.symbol}, qty={order.qty}")
        assert order.state == OrderState.FILLED, "PaperBroker should fill immediately at last_price"

        # ---------- 7. inspect broker portfolio ----------
        _hr("6. inspect broker (position should exist)")

        portfolio = await pb.get_portfolio()
        print(f"  cash: {portfolio.cash}")
        print(f"  positions:")
        for pos in portfolio.positions:
            print(
                f"    {pos.symbol}: qty={pos.qty}, avg_cost={pos.avg_cost}"
            )
        assert any(p.symbol == "AAPL" and p.qty == Decimal("5") for p in portfolio.positions)

        # ---------- 8. inspect pending_signals (promoted) ----------
        _hr("7. inspect pending_signals (status=promoted, order linked)")

        await session.refresh(pending_rows[0])
        refreshed = pending_rows[0]
        print(
            f"  pending: id={refreshed.id}, status={refreshed.status}, "
            f"resulting_client_order_id={refreshed.resulting_client_order_id}"
        )
        assert refreshed.status == "promoted"
        assert refreshed.resulting_client_order_id == order.client_order_id

        # ---------- 9. inspect audit chain ----------
        _hr("8. inspect actions audit (promote_signal entry, no nested submit_order)")

        actions = (
            await session.execute(select(Action).order_by(Action.ts))
        ).scalars().all()
        for a in actions:
            print(
                f"  action: capability={a.capability}, "
                f"actor={a.actor_id}/{a.actor_type}, outcome={a.outcome_status}"
            )
        # Exactly one promote_signal audit row, no submit_order
        # (promote_signal calls broker directly, not the submit_order
        # capability, so there is no double-audit.)
        promote_audits = [a for a in actions if a.capability == "promote_signal"]
        submit_audits = [a for a in actions if a.capability == "submit_order"]
        assert len(promote_audits) == 1
        assert promote_audits[0].outcome_status == "ok"
        assert promote_audits[0].reasoning == (
            "e2e selftest: manual promotion of pending dry-run signal"
        )
        assert len(submit_audits) == 0, (
            "promote_signal does NOT go through submit_order capability "
            "internally — that would double-audit a single user action"
        )

        # ---------- 10. inspect dossier persisted ----------
        _hr("9. inspect decisions (one dossier, mode=dry_run)")
        decisions = (await session.execute(select(Decision))).scalars().all()
        for d in decisions:
            print(
                f"  decision: id={d.id}, event_id={d.event_id}, "
                f"mode={d.mode}, actor={d.actor_id}"
            )
        assert len(decisions) == 1
        assert decisions[0].mode == "dry_run"

    await engine.dispose()

    _hr("ALL ASSERTIONS PASSED — full pipeline ran end-to-end")
    print()
    print(" event -> dossier -> route(dry_run) -> pending -> promote -> broker -> audit")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
