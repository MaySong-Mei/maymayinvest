"""Capture an event into the determinism corpus.

Per the approved amendment 2026-05-23-amend-bin3-rule-defer-aggregator.md.

Runs the analyzer N=3 times serially over one event, writes a markdown
stub to v1/docs/evals/analyzer-determinism-corpus/<date>-<slug>.md.

The stub has a blank "Operator's manual pick" section. The operator
opens it, reads the 3 reasoning chains, writes their pick + 1-3
sentences of why, and commits.

Usage:
    python scripts/capture_event_to_corpus.py --event PATH [options]

Required env: CLAUDE_CODE_OAUTH_TOKEN
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

_REPO_BACKEND = Path(__file__).resolve().parent.parent
if str(_REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(_REPO_BACKEND))

from app.brokers.paper import PaperBroker  # noqa: E402
from app.domain.event import Event, EventKind  # noqa: E402
from app.intel.analyzer.base import AnalyzerContext  # noqa: E402
from app.intel.analyzer.claude_code import ClaudeCodeAnalyzer  # noqa: E402

N_TRIALS = 3
CORPUS_DIR = _REPO_BACKEND.parent / "docs" / "evals" / "analyzer-determinism-corpus"


def _slug(s: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:maxlen] or "event"


def _make_event_from_payload(payload: dict) -> Event:
    """Build an Event from a fixture payload. Supports both EDGAR-shaped
    fixtures and minimal {kind, headline, payload, ...} shapes."""
    if "filer" in payload and "filed_at" in payload:
        # EDGAR-shaped (matches tests/fixtures/edgar_8k_*.json)
        ts_str = payload.get("accepted_at") or payload.get("filed_at")
        return Event(
            kind=EventKind.EDGAR_8K,
            source="manual",
            external_id=f"manual:{payload['filer']['ticker'].lower()}-"
                        f"{_slug(payload['headline'], 30)}-{ts_str}",
            ts=datetime.fromisoformat(ts_str).astimezone(UTC),
            symbols=[payload["filer"]["ticker"]],
            headline=payload["headline"],
            payload=payload,
        )
    # Minimal shape
    return Event(
        kind=EventKind(payload.get("kind", "test_synthetic")),
        source=payload.get("source", "manual"),
        external_id=payload["external_id"],
        ts=datetime.fromisoformat(payload["ts"]).astimezone(UTC),
        symbols=payload.get("symbols", []),
        headline=payload["headline"],
        payload=payload.get("payload", payload),
    )


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True, help="Event JSON file")
    parser.add_argument("--timeout", type=int, default=120, help="Per-trial timeout (s)")
    parser.add_argument(
        "--price",
        action="append",
        default=[],
        metavar="SYMBOL=PRICE",
        help="Seed broker price, e.g. AAPL=220.50 (repeatable)",
    )
    args = parser.parse_args()

    payload = json.loads(args.event.read_text(encoding="utf-8"))
    event = _make_event_from_payload(payload)

    pb = PaperBroker()
    for entry in args.price:
        sym, _, px = entry.partition("=")
        pb.set_last_price(sym.strip(), Decimal(px.strip()))

    async def snapshot_provider(_ev):
        portfolio = await pb.get_portfolio()
        recent = {}
        for sym in event.symbols:
            try:
                px = await pb.get_last_price(sym)
                recent[sym] = [str(px)]
            except Exception:
                pass
        return {
            "portfolio": {
                "cash": str(portfolio.cash),
                "positions": [
                    {"symbol": p.symbol, "qty": str(p.qty), "avg_cost": str(p.avg_cost)}
                    for p in portfolio.positions
                ],
            },
            "recent_prices": recent,
        }

    analyzer = ClaudeCodeAnalyzer(timeout_seconds=args.timeout)
    trials = []
    print(f"running {N_TRIALS} trials on {event.external_id}...")
    for i in range(N_TRIALS):
        ctx = AnalyzerContext(
            actor_id=f"corpus-capture-trial-{i+1}",
            snapshot_provider=snapshot_provider,
        )
        try:
            dossier = await analyzer.analyze(event, ctx)
            trials.append({
                "trial_no": i + 1,
                "mode": dossier.mode,
                "intent_is_null": dossier.proposed.intent is None,
                "confidence": str(dossier.confidence),
                "alternatives_count": len(dossier.alternatives_considered),
                "skills_count": len(dossier.skills_invoked),
                "latency_ms": dossier.latency_ms,
                "intent": (
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
                "reasoning_first_300": dossier.reasoning_chain[:300],
                "reasoning_chain_full": dossier.reasoning_chain,
            })
            print(f"  trial {i+1}: mode={dossier.mode}, "
                  f"intent={'null' if dossier.proposed.intent is None else 'set'}, "
                  f"conf={dossier.confidence}")
        except Exception as exc:
            trials.append({"trial_no": i + 1, "error": f"{type(exc).__name__}: {exc}"})
            print(f"  trial {i+1}: ERROR {exc}")

    # Write markdown stub
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = CORPUS_DIR / f"{today}-{_slug(event.headline, 40)}.md"

    lines = [
        f"# Corpus entry: {event.headline}",
        "",
        f"- event_id: `{event.external_id}`",
        f"- kind: {event.kind.value}",
        f"- ts: {event.ts.isoformat()}",
        f"- captured: {datetime.now(UTC).isoformat()}",
        f"- snapshot prices: {args.price or 'none'}",
        "",
        "## Trials",
        "",
        "| # | mode | intent | conf | alt | lat (ms) |",
        "|---|---|---|---|---|---|",
    ]
    for t in trials:
        if "error" in t:
            lines.append(f"| {t['trial_no']} | ERROR | — | — | — | — |")
            continue
        intent_str = (
            f"{t['intent']['side']} {t['intent']['qty']} {t['intent']['type']}"
            if t["intent"]
            else "—"
        )
        lines.append(
            f"| {t['trial_no']} | {t['mode']} | {intent_str} | "
            f"{t['confidence']} | {t['alternatives_count']} | {t['latency_ms']} |"
        )
    lines.append("")
    lines.append("## Reasoning chains (first 300 chars)")
    lines.append("")
    for t in trials:
        if "error" in t:
            lines.append(f"### Trial {t['trial_no']}: ERROR")
            lines.append(f"`{t['error']}`")
        else:
            lines.append(f"### Trial {t['trial_no']}")
            lines.append("")
            lines.append(t["reasoning_first_300"] + "...")
        lines.append("")
    lines.append("## Operator's manual pick")
    lines.append("")
    lines.append("**TO FILL IN BY HAND** before committing.")
    lines.append("")
    lines.append("Pick which trial (or none): _")
    lines.append("")
    lines.append("Why (1-3 sentences):")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("<details><summary>full reasoning chains (for the operator's pick)</summary>")
    lines.append("")
    for t in trials:
        if "error" in t:
            continue
        lines.append(f"#### Trial {t['trial_no']} full")
        lines.append("")
        lines.append(t["reasoning_chain_full"])
        lines.append("")
    lines.append("</details>")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote stub: {out_path}")
    print("Now open the file, fill in the 'Operator's manual pick' section, and commit.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
