"""Run N=5 ClaudeCodeAnalyzer trials over the same event/snapshot.

Pre-registered analysis plan: v1/docs/evals/analyzer-determinism-eval-plan-2026-05-23.md
This script runs the experiment exactly as the plan defines it. No
analysis adjustments; the script outputs raw JSON. The bin assignment
and writeup happen separately.

Inputs (fixed per plan):
  - Event: tests/fixtures/edgar_8k_aapl_buyback_2024.json
  - Snapshot: empty portfolio + AAPL last_price = Decimal("220.50")
    (kept consistent with run-1 / run-2 for comparability; the dev
    seed was removed for production in commit 1e9bd92 but this
    experiment explicitly re-creates that snapshot to test the
    determinism question over identical inputs.)
  - Analyzer prompt version: v1-2026-05-23
  - Timeout: 120s per trial
  - Concurrency: serial

Output:
  - v1/docs/evals/analyzer-determinism-results-2026-05-23.json
    containing one record per trial with all pre-registered features
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import UTC, datetime, timezone
from decimal import Decimal
from pathlib import Path

_REPO_BACKEND = Path(__file__).resolve().parent.parent
if str(_REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(_REPO_BACKEND))

from app.brokers.paper import PaperBroker
from app.domain.event import Event, EventKind
from app.intel._subprocess import SubprocessError
from app.intel.analyzer.base import AnalyzerContext
from app.intel.analyzer.claude_code import ClaudeCodeAnalyzer

FIXTURE_PATH = _REPO_BACKEND / "tests" / "fixtures" / "edgar_8k_aapl_buyback_2024.json"
N_TRIALS = 5
TIMEOUT_SECONDS = 120


async def run_one_trial(trial_no: int, event: Event, broker: PaperBroker) -> dict:
    """Run one analyzer call. Returns the recorded outcome features.

    The features recorded match the pre-registered set in the plan doc.
    Subprocess / parse errors are captured (not re-raised) — per plan
    they count as bin-4 triggers and the experiment continues.
    """
    print(f"  trial {trial_no}: ", end="", flush=True)

    async def snapshot_provider(ev):
        # Identical to the snapshot used in the prior two real runs
        # (commits 5ae95c3 + b53075b). Comparability requires same input.
        portfolio = await broker.get_portfolio()
        return {
            "portfolio": {
                "cash": str(portfolio.cash),
                "positions": [
                    {
                        "symbol": p.symbol,
                        "qty": str(p.qty),
                        "avg_cost": str(p.avg_cost),
                    }
                    for p in portfolio.positions
                ],
            },
            "recent_prices": {"AAPL": [str(await broker.get_last_price("AAPL"))]},
        }

    analyzer = ClaudeCodeAnalyzer(timeout_seconds=TIMEOUT_SECONDS)
    ctx = AnalyzerContext(
        actor_id=f"determinism-trial-{trial_no}",
        snapshot_provider=snapshot_provider,
        record_llm_call=None,  # not persisting llm_calls for this experiment
    )

    t0 = time.monotonic()
    error: str | None = None
    dossier = None
    try:
        dossier = await analyzer.analyze(event, ctx)
    except SubprocessError as exc:
        error = f"SubprocessError: {exc}"
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    latency_ms = int((time.monotonic() - t0) * 1000)

    if error is not None:
        print(f"ERROR ({latency_ms}ms): {error[:80]}")
        return {
            "trial_no": trial_no,
            "error": error,
            "latency_ms": latency_ms,
        }

    record = {
        "trial_no": trial_no,
        "dossier_id": str(dossier.id),
        "mode": dossier.mode,
        "intent_is_null": dossier.proposed.intent is None,
        "confidence": str(dossier.confidence),
        "alternatives_count": len(dossier.alternatives_considered),
        "skills_count": len(dossier.skills_invoked),
        "latency_ms": latency_ms,
        "reasoning_first_200_chars": dossier.reasoning_chain[:200],
        "error": None,
    }
    if dossier.proposed.intent is not None:
        record["intent"] = {
            "symbol": dossier.proposed.intent.symbol,
            "side": dossier.proposed.intent.side.value,
            "qty": str(dossier.proposed.intent.qty),
            "type": dossier.proposed.intent.type.value,
            "limit_price": (
                str(dossier.proposed.intent.limit_price)
                if dossier.proposed.intent.limit_price is not None
                else None
            ),
        }
    else:
        record["intent"] = None
        record["no_action_reason"] = dossier.proposed.no_action_reason
    print(
        f"mode={record['mode']}, intent={'null' if record['intent_is_null'] else 'set'}, "
        f"conf={record['confidence']}, lat={latency_ms}ms"
    )
    return record


async def main() -> int:
    if not FIXTURE_PATH.exists():
        print(f"FATAL: fixture not found at {FIXTURE_PATH}")
        return 1

    # Build event (identical to selftest_e2e.py)
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

    # Broker with explicit AAPL price (NOT the removed _DEV_QUOTES seed —
    # this is the experiment explicitly recreating the snapshot used by
    # run-1 and run-2 for comparability)
    broker = PaperBroker()
    broker.set_last_price("AAPL", Decimal("220.50"))

    print("=" * 70)
    print(f" analyzer determinism experiment, N={N_TRIALS}")
    print(f" event: {event.external_id}")
    print(f" plan: v1/docs/evals/analyzer-determinism-eval-plan-2026-05-23.md")
    print("=" * 70)

    trials = []
    overall_start = time.monotonic()
    for i in range(1, N_TRIALS + 1):
        record = await run_one_trial(i, event, broker)
        trials.append(record)
    overall_elapsed = time.monotonic() - overall_start

    # Save raw output. Bin assignment + writeup happens separately.
    out_dir = _REPO_BACKEND.parent / "docs" / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / f"analyzer-determinism-results-{today}.json"
    out_path.write_text(
        json.dumps(
            {
                "experiment": "analyzer-determinism-N5",
                "plan": "v1/docs/evals/analyzer-determinism-eval-plan-2026-05-23.md",
                "run_at_utc": datetime.now(timezone.utc).isoformat(),
                "analyzer_prompt_version": "v1-2026-05-23",
                "event_external_id": event.external_id,
                "snapshot_aapl_last_price": "220.50",
                "n_trials": N_TRIALS,
                "timeout_seconds_per_trial": TIMEOUT_SECONDS,
                "overall_elapsed_seconds": overall_elapsed,
                "trials": trials,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print(f" {N_TRIALS} trials complete in {overall_elapsed:.1f}s")
    print(f" results: {out_path}")
    print("=" * 70)
    print()
    print(" NEXT STEP (per pre-reg plan):")
    print("   1. Write the analysis table FIRST")
    print("   2. Compute bin assignment per the locked rules")
    print("   3. Write the prose section LAST")
    print("   File: v1/docs/evals/analyzer-determinism-results-2026-05-23.md")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
