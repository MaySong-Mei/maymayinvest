"""First-time: run reviewer over a real (non-stub) DecisionDossier.

PHILOSOPHY.md identifies the project's "hardest unsolved problem" as
whether the reviewer can judge right-bet from information-only basis.
Until now, the reviewer was only tested on hand-crafted fixtures
(5/5 PASS at prompt v1-2026-05-22). This script runs the reviewer
on output from ClaudeCodeAnalyzer over a real 8-K — the first such
test.

Specifically watch:
  - Does the reviewer catch the inconsistency surfaced in the
    analyzer's own reasoning chain? The analyzer noted the
    snapshot_provider price ($220.50) was stale relative to the
    2024-05-02 event but still sized the probe using that stale
    price. A careful reviewer should flag
    'reasoning_doesnt_follow_through_on_own_warning' or similar.

  - Does the reviewer treat the analyzer's confidence (0.6) as
    calibrated? The reasoning flagged real risks but still proposed
    a tiny probe — 0.6 seems calibrated to operator's hand-eye but
    the reviewer is independent.

  - Does the reviewer raise any flags the operator hand-eyed didn't
    surface?

Output:
  - Prints verdict + reasoning to stdout
  - Saves full reviewer output JSON to v1/docs/evals/

Pre-conditions: CLAUDE_CODE_OAUTH_TOKEN set (same as analyzer).
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime, timezone
from decimal import Decimal
from pathlib import Path

_REPO_BACKEND = Path(__file__).resolve().parent.parent
if str(_REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(_REPO_BACKEND))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.brokers.paper import PaperBroker
from app.domain.event import Event, EventKind
from app.engine.broker_registry import reset_kill_switch, set_broker
from app.intel.analyzer.base import AnalyzerContext
from app.intel.analyzer.claude_code import ClaudeCodeAnalyzer
from app.intel.review_pipeline import review_decision
from app.intel.reviewer.base import ReviewerContext
from app.intel.reviewer.claude_code import ClaudeCodeReviewer
from app.intel.reviewer.prompt import (
    CURRENT_PROMPT_VERSION as REVIEWER_PROMPT_VERSION,
)
from app.persistence.models import Base
from app.persistence.repositories.decisions import save_dossier, save_llm_call
from app.persistence.repositories.events import save_event


FIXTURE_PATH = _REPO_BACKEND / "tests" / "fixtures" / "edgar_8k_aapl_buyback_2024.json"


async def main() -> int:
    print("=" * 70)
    print(" reviewer-on-real-dossier — first such run")
    print("=" * 70)

    # bootstrap
    pb = PaperBroker()
    pb.set_last_price("AAPL", Decimal("220.50"))
    set_broker(pb)
    reset_kill_switch()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as session:
        # load fixture + event
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        event = Event(
            kind=EventKind.EDGAR_8K,
            source="manual",
            external_id=f"manual:aapl-buyback-{payload['accepted_at']}",
            ts=datetime.fromisoformat(payload["accepted_at"]).astimezone(UTC),
            symbols=[payload["filer"]["ticker"]],
            headline=payload["headline"],
            payload=payload,
        )
        await save_event(session, event)

        # analyze
        async def llm_recorder(call):
            await save_llm_call(session, call)

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
                "recent_prices": {payload["filer"]["ticker"]: [str(await pb.get_last_price(payload["filer"]["ticker"]))]},
            }

        print("\n[step 1] running ClaudeCodeAnalyzer...")
        analyzer = ClaudeCodeAnalyzer(timeout_seconds=120)
        actx = AnalyzerContext(
            actor_id="review-test-analyzer",
            snapshot_provider=snapshot_provider,
            record_llm_call=llm_recorder,
        )
        dossier = await analyzer.analyze(event, actx)
        await save_dossier(session, dossier)
        print(f"  dossier {dossier.id}: mode={dossier.mode}, conf={dossier.confidence}")
        print(f"  analyzer latency: {dossier.latency_ms}ms")

        # review
        print("\n[step 2] running ClaudeCodeReviewer over the dossier...")
        reviewer = ClaudeCodeReviewer(timeout_seconds=120)
        rctx = ReviewerContext(
            actor_id="real-dossier-reviewer",
            prompt_version=REVIEWER_PROMPT_VERSION,
        )

        review = await review_decision(session, reviewer, dossier.id, rctx)

        print(f"  verdict: {review.verdict.value}")
        print(f"  reviewer confidence: {review.confidence}")
        print(f"  flags: {review.flags}")
        print()
        print("[reasoning]")
        for line in review.reasoning.splitlines():
            print(f"  {line}")

        # persist eval output
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_dir = _REPO_BACKEND.parent / "docs" / "evals"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"reviewer-on-real-dossier-{today}.json"
        out_path.write_text(
            json.dumps(
                {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "analyzer_prompt_version": "v1-2026-05-23",
                    "reviewer_prompt_version": REVIEWER_PROMPT_VERSION,
                    "event_external_id": event.external_id,
                    "analyzer_latency_ms": dossier.latency_ms,
                    "dossier": {
                        "id": str(dossier.id),
                        "mode": dossier.mode,
                        "confidence": str(dossier.confidence),
                        "event_summary": dossier.event_summary,
                        "reasoning_chain": dossier.reasoning_chain,
                        "alternatives_considered": [
                            {"action": a.action, "rejected_because": a.rejected_because}
                            for a in dossier.alternatives_considered
                        ],
                        "skills_invoked": [
                            {"name": s.name, "version": s.version} for s in dossier.skills_invoked
                        ],
                        "proposed_intent": (
                            {
                                "symbol": dossier.proposed.intent.symbol,
                                "side": dossier.proposed.intent.side.value,
                                "qty": str(dossier.proposed.intent.qty),
                                "type": dossier.proposed.intent.type.value,
                            }
                            if dossier.proposed.intent
                            else None
                        ),
                        "no_action_reason": dossier.proposed.no_action_reason,
                    },
                    "review": {
                        "verdict": review.verdict.value,
                        "reasoning": review.reasoning,
                        "flags": list(review.flags),
                        "confidence": str(review.confidence),
                    },
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        print(f"\nwritten to: {out_path}")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
