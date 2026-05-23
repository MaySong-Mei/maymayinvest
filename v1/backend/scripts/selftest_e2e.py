"""End-to-end selftest: real 8-K -> ClaudeCodeAnalyzer -> dossier -> route ->
promote -> broker fill -> audit.

UPGRADED 2026-05-23. Previous version used StubAnalyzer + object.__setattr__
hack to force mode='dry_run' with a hand-built intent — that demonstrated
the *plumbing* but not the *decision pipeline*. The hack is now gone:
ClaudeCodeAnalyzer reads a real 8-K JSON fixture and produces an actionable
dossier on its own. This is the v1 success-criterion shape the dialogue
reviewer (a26ded8154a8298b5 + ad4ba152aaf8e3353) demanded.

Pipeline:
  1. Load real 8-K JSON from tests/fixtures/edgar_8k_aapl_buyback_2024.json.
  2. Construct Event (kind=edgar_8k, source='manual' marking hand-curated).
  3. Persist via save_event (idempotent).
  4. ClaudeCodeAnalyzer.analyze(event, ctx) -> DecisionDossier.
     - Spawns `claude -p` subprocess via shared subprocess plumbing.
     - Requires CLAUDE_CODE_OAUTH_TOKEN in env (see _build_subprocess_env).
     - Records llm_calls trace.
  5. route_decision dispatches by dossier.mode.
     - If dossier.mode is dry_run/notify, pending_signal is enqueued.
     - If dossier.mode is auto with intent, broker is called via router
       (path not exercised by default; analyzer chooses mode).
  6. If pending_signal exists, promote_signal capability is called by the
     user to execute the order.
  7. Inspect broker, audit log, pending_signals state.

This script is end-to-end. It hits real `claude -p` and burns subscription
budget (~$0.10-0.30 per run for the analyze call). Don't run in tight
loops; it's a manual integrity check.

Pre-conditions:
  - CLAUDE_CODE_OAUTH_TOKEN must be set in env (see eval-doc 2026-05-22
    addendum on setup-token).
  - claude binary on PATH or in a known location.
"""
from __future__ import annotations

import asyncio
import json
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
from app.domain.event import Event, EventKind
from app.engine.broker_registry import reset_kill_switch, set_broker
from app.intel.adapters import OperatorOrderSubmitter
from app.intel.analyzer.base import AnalyzerContext
from app.intel.analyzer.claude_code import ClaudeCodeAnalyzer
from app.intel.router import RouterContext, route_decision
from app.operator.capabilities import PromoteSignalReq, promote_signal
from app.operator.context import OperatorContext
from app.persistence.models import Action, Base, Decision, PendingSignal
from app.persistence.repositories.decisions import save_llm_call
from app.persistence.repositories.events import save_event


FIXTURE_PATH = _REPO_BACKEND / "tests" / "fixtures" / "edgar_8k_aapl_buyback_2024.json"


def _hr(title: str) -> None:
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


async def main() -> int:
    # ---------- 0. bootstrap ----------
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
        # ---------- 1. load fixture + synthesize event ----------
        _hr(f"1. load 8-K fixture ({FIXTURE_PATH.name})")
        if not FIXTURE_PATH.exists():
            print(f"  FATAL: fixture not found at {FIXTURE_PATH}")
            return 1

        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        ticker = payload["filer"]["ticker"]
        print(f"  loaded: {payload['headline'][:80]}")
        print(f"  filer: {payload['filer']['name']} ({ticker})")
        print(f"  items: {payload.get('items', [])}")

        event = Event(
            kind=EventKind.EDGAR_8K,
            # source='manual' marks this as hand-curated; future EDGAR poller
            # would use source='sec_edgar'.
            source="manual",
            external_id=f"manual:aapl-buyback-{payload['accepted_at']}",
            ts=datetime.fromisoformat(payload["accepted_at"]).astimezone(UTC),
            symbols=[ticker],
            headline=payload["headline"],
            payload=payload,
        )
        await save_event(session, event)
        print(f"  event saved: external_id={event.external_id}")

        # ---------- 2. analyze via real ClaudeCodeAnalyzer ----------
        _hr("2. ClaudeCodeAnalyzer.analyze (real claude -p, expect 20-40s)")

        # llm_call recorder writes to llm_calls table once we have a session.
        # Note: the analyzer writes the call BEFORE we save the dossier,
        # so decision_id references a not-yet-persisted row — that's fine
        # because both insertions happen in the same transaction before commit.
        async def llm_recorder(call):
            await save_llm_call(session, call)

        # Snapshot provider for v1: minimal portfolio + recent prices. Real
        # production would join market data here.
        async def snapshot_provider(ev):
            portfolio = await pb.get_portfolio()
            return {
                "portfolio": {
                    "cash": str(portfolio.cash),
                    "positions": [
                        {"symbol": p.symbol, "qty": str(p.qty), "avg_cost": str(p.avg_cost)}
                        for p in portfolio.positions
                    ],
                },
                "recent_prices": {
                    ticker: [str(await pb.get_last_price(ticker))]
                },
            }

        analyzer = ClaudeCodeAnalyzer(timeout_seconds=120)
        actx = AnalyzerContext(
            actor_id="selftest-cc-analyzer",
            snapshot_provider=snapshot_provider,
            record_llm_call=llm_recorder,
        )

        import time as _time
        t0 = _time.monotonic()
        dossier = await analyzer.analyze(event, actx)
        elapsed = _time.monotonic() - t0
        print(f"  analyzed in {elapsed:.1f}s")
        print(f"  dossier id: {dossier.id}")
        print(f"  event_summary: {dossier.event_summary}")
        print(f"  mode: {dossier.mode}")
        print(f"  confidence: {dossier.confidence}")
        if dossier.proposed.intent is not None:
            i = dossier.proposed.intent
            print(f"  proposed: {i.symbol} {i.side.value} {i.qty} ({i.type.value})")
        else:
            print(f"  proposed: no action — {dossier.proposed.no_action_reason}")
        print(f"  alternatives_considered ({len(dossier.alternatives_considered)}):")
        for alt in dossier.alternatives_considered:
            print(f"    - {alt.action}: {alt.rejected_because[:80]}")
        print(f"  reasoning excerpt:")
        for line in dossier.reasoning_chain.splitlines()[:5]:
            print(f"    {line}")
        if len(dossier.reasoning_chain.splitlines()) > 5:
            print(f"    ... ({len(dossier.reasoning_chain.splitlines())} lines total)")

        # ---------- 3. route ----------
        _hr(f"3. route_decision (mode={dossier.mode})")

        submitter = OperatorOrderSubmitter(session=session, actor_id="auto-router")
        rctx = RouterContext(session=session, submitter=submitter, actor_id="selftest")
        result = await route_decision(rctx, dossier)
        print(f"  route result: {result}")

        # ---------- 4 + 5: branch by mode ----------
        if dossier.mode in ("notify", "dry_run"):
            _hr(f"4. inspect pending_signals (should be 1 row, mode={dossier.mode})")
            pending_rows = (await session.execute(select(PendingSignal))).scalars().all()
            for row in pending_rows:
                print(
                    f"  pending: id={row.id}, dossier_id={row.dossier_id}, "
                    f"mode={row.mode}, status={row.status}"
                )
            assert len(pending_rows) == 1
            assert pending_rows[0].status == "pending"
            signal_id = pending_rows[0].id

            # If dossier has an intent, we can promote. If not (no-action
            # decision), there's nothing to promote; selftest ends here.
            if dossier.proposed.intent is None:
                _hr("5. dossier is no-action; selftest ends here (no promotion)")
                _hr("RESULT")
                print(f"  pipeline ran through ANALYZE + ROUTE for no-action dossier")
                print(f"  events 1, decisions 1 (mode={dossier.mode}), pending 1, llm_calls 1")
                return 0

            _hr("5. promote_signal capability (user-initiated)")
            op_ctx = OperatorContext(
                actor_id="me",
                actor_type="user",
                session=session,
                reasoning="e2e selftest: manual promotion after real CC analysis",
            )
            order = await promote_signal(op_ctx, PromoteSignalReq(pending_signal_id=signal_id))
            print(f"  order returned: client_order_id={order.client_order_id}")
            print(f"    state={order.state.value}, symbol={order.symbol}, qty={order.qty}")

            # Pending should now be promoted
            await session.refresh(pending_rows[0])
            print(f"  pending after promote: status={pending_rows[0].status}")
            assert pending_rows[0].status == "promoted"
        elif dossier.mode == "auto":
            _hr("4. auto-mode dossier (router already submitted)")
            assert result.order is not None or result.risk_blocked, (
                "auto mode must either submit or be risk-blocked"
            )

        # ---------- 6. inspect broker portfolio ----------
        _hr("6. inspect broker (position state)")
        portfolio = await pb.get_portfolio()
        print(f"  cash: {portfolio.cash}")
        print(f"  positions:")
        if not portfolio.positions:
            print(f"    (none)")
        for pos in portfolio.positions:
            print(f"    {pos.symbol}: qty={pos.qty}, avg_cost={pos.avg_cost}")

        # ---------- 7. inspect audit chain ----------
        _hr("7. inspect actions audit")
        actions = (await session.execute(select(Action).order_by(Action.ts))).scalars().all()
        for a in actions:
            print(
                f"  action: capability={a.capability}, "
                f"actor={a.actor_id}/{a.actor_type}, outcome={a.outcome_status}"
            )

        # ---------- 8. inspect llm_calls ----------
        _hr("8. inspect llm_calls (trace of analyzer subprocess call)")
        from app.persistence.models import LlmCallLog
        llm_calls = (await session.execute(select(LlmCallLog))).scalars().all()
        print(f"  rows: {len(llm_calls)}")
        for c in llm_calls:
            print(
                f"  llm_call: purpose={c.purpose}, model={c.model}, "
                f"latency_ms={c.latency_ms}, response_len={len(c.response or '')}"
            )

        # ---------- 9. inspect decisions ----------
        _hr("9. inspect decisions (one dossier)")
        decisions = (await session.execute(select(Decision))).scalars().all()
        for d in decisions:
            print(
                f"  decision: id={d.id}, event_id={d.event_id}, "
                f"mode={d.mode}, actor={d.actor_id}, latency_ms={d.latency_ms}"
            )
        assert len(decisions) == 1

    await engine.dispose()

    _hr("ALL ASSERTIONS PASSED — full pipeline ran end-to-end ON REAL ANALYZER")
    print()
    print(" event(real 8-K) -> ClaudeCodeAnalyzer -> dossier -> route -> [promote] -> broker -> audit")
    print(" Hack-free: no object.__setattr__, no synthetic intent injection.")
    print(" The analyzer chose mode, intent (or no-action), confidence, and reasoning all on its own.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
