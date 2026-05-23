"""Drive ClaudeCodeReviewer over the hand-labeled eval set.

Runs each case in tests/eval/reviewer_eval_set.py through the real
`claude -p` subprocess. Captures: verdict, reasoning, flags,
confidence, latency, parse failures.

Why this script exists (vs unit tests with mocked subprocess):
  Unit tests verify the parser, the subprocess plumbing, the JSON
  shape contract. They cannot verify that the reviewer prompt actually
  elicits useful judgments from a real LLM. This script does the
  empirical part — exactly once per prompt version, with results
  archived to v1/docs/evals/.

Output:
  - prints a summary table to stdout
  - writes the full per-case results to a JSON file in the path
    given by --out (default: v1/docs/evals/reviewer-v1-<date>.json)

Usage:
  python scripts/eval_reviewer.py [--out PATH] [--timeout SECONDS]

This script is NOT a pytest test. It hits the real Claude Code
subscription and is meant to be run manually when evaluating a
reviewer prompt version. Adding it to CI would be flaky and would
burn rate-limited budget.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.intel.reviewer.base import ReviewerContext
from app.intel.reviewer.claude_code import (
    ClaudeCodeReviewer,
    ReviewerError,
)
from app.intel.reviewer.prompt import CURRENT_PROMPT_VERSION
from app.persistence.repositories.decisions import (
    _strip_outcome_leaks,  # use the same stripping the real path uses
)

# Import the eval set. Path resolution: add backend/ to sys.path if needed.
_REPO_BACKEND = Path(__file__).resolve().parent.parent
if str(_REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(_REPO_BACKEND))

from tests.eval.reviewer_eval_set import ALL_CASES, EvalCase  # noqa: E402


@dataclass
class CaseResult:
    name: str
    expected_verdict: str
    expected_flags_subset: list[str]
    rationale_for_expected: str
    actual_verdict: str | None = None
    actual_reasoning: str | None = None
    actual_flags: list[str] = field(default_factory=list)
    actual_confidence: float | None = None
    matched_expected: bool | None = None
    matched_flag_subset: bool | None = None
    latency_seconds: float = 0.0
    error: str | None = None


def _build_reviewer_input_from_dossier(case: EvalCase) -> dict:
    """Construct the outcome-blind reviewer input WITHOUT touching the DB.

    This mirrors what build_reviewer_input(session, id) returns, but for
    a hand-crafted in-memory dossier. We use the same _strip_outcome_leaks
    helper to guarantee the eval substrate is the same as production.
    """
    d = case.dossier
    return {
        "decision_id": str(d.id),
        "created_at": d.created_at.isoformat(),
        "event_kind": d.event_kind,
        "event_summary": d.event_summary,
        "available_info_snapshot": _strip_outcome_leaks(d.available_info_snapshot),
        "reasoning_chain": d.reasoning_chain,
        "alternatives_considered": [a.model_dump() for a in d.alternatives_considered],
        "confidence": str(d.confidence),
        "skills_invoked": [s.model_dump() for s in d.skills_invoked],
        "proposed": _strip_outcome_leaks(d.proposed.model_dump(mode="json")),
        "mode": d.mode,
    }


async def run_case(
    case: EvalCase,
    reviewer: ClaudeCodeReviewer,
    ctx: ReviewerContext,
) -> CaseResult:
    result = CaseResult(
        name=case.name,
        expected_verdict=case.expected_verdict,
        expected_flags_subset=list(case.expected_flags_subset),
        rationale_for_expected=case.rationale,
    )

    reviewer_input = _build_reviewer_input_from_dossier(case)
    start = time.monotonic()
    try:
        review = await reviewer.review(reviewer_input, ctx)
    except ReviewerError as exc:
        result.latency_seconds = time.monotonic() - start
        result.error = f"ReviewerError: {exc}"
        return result
    except Exception as exc:  # noqa: BLE001
        result.latency_seconds = time.monotonic() - start
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    result.latency_seconds = time.monotonic() - start
    result.actual_verdict = review.verdict.value
    result.actual_reasoning = review.reasoning
    result.actual_flags = list(review.flags)
    result.actual_confidence = float(review.confidence)
    result.matched_expected = review.verdict.value == case.expected_verdict
    if case.expected_flags_subset:
        result.matched_flag_subset = any(
            f in review.flags for f in case.expected_flags_subset
        )
    return result


def format_summary(results: list[CaseResult]) -> str:
    lines = []
    lines.append("")
    lines.append("=" * 76)
    lines.append(" REVIEWER EVAL — SUMMARY")
    lines.append("=" * 76)
    lines.append(
        f"{'case':<38} {'expected':<11} {'actual':<11} {'match':<6} {'lat':>6}"
    )
    lines.append("-" * 76)
    for r in results:
        actual = r.actual_verdict or ("ERROR" if r.error else "—")
        match = (
            "PASS"
            if r.matched_expected
            else ("FAIL" if r.matched_expected is False else "—")
        )
        lat = f"{r.latency_seconds:>5.1f}s"
        lines.append(
            f"{r.name:<38} {r.expected_verdict:<11} {actual:<11} {match:<6} {lat:>6}"
        )

    lines.append("-" * 76)
    matched = sum(1 for r in results if r.matched_expected)
    errors = sum(1 for r in results if r.error)
    total = len(results)
    avg_lat = sum(r.latency_seconds for r in results) / max(total, 1)
    lines.append(
        f"matched: {matched}/{total}    errors: {errors}    avg latency: {avg_lat:.1f}s"
    )

    # Per-case flag subset matches
    flag_checks = [r for r in results if r.expected_flags_subset]
    if flag_checks:
        lines.append("")
        lines.append("Expected-flag-subset matches:")
        for r in flag_checks:
            mark = "PASS" if r.matched_flag_subset else "FAIL"
            lines.append(
                f"  {r.name:<38} {mark}  expected any of "
                f"{r.expected_flags_subset}; got {r.actual_flags}"
            )
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON output path (default v1/docs/evals/reviewer-<prompt-version>-<date>.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="seconds per case (default 120; cold start can be slow)",
    )
    args = parser.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if args.out is None:
        # default lives next to the eval analysis markdown
        out_dir = _REPO_BACKEND.parent / "docs" / "evals"
        out_dir.mkdir(parents=True, exist_ok=True)
        args.out = out_dir / f"reviewer-{CURRENT_PROMPT_VERSION}-{today}-results.json"

    reviewer = ClaudeCodeReviewer(timeout_seconds=args.timeout)
    ctx = ReviewerContext(
        actor_id="eval-driver",
        prompt_version=CURRENT_PROMPT_VERSION,
    )

    print(
        f"running {len(ALL_CASES)} cases against {CURRENT_PROMPT_VERSION} "
        f"(timeout={args.timeout}s per case)..."
    )
    results: list[CaseResult] = []
    for case in ALL_CASES:
        print(f"  -> {case.name} ... ", end="", flush=True)
        r = await run_case(case, reviewer, ctx)
        results.append(r)
        status = (
            "PASS"
            if r.matched_expected
            else ("FAIL" if r.matched_expected is False else f"ERR: {r.error}")
        )
        print(f"{status} ({r.latency_seconds:.1f}s)")

    summary = format_summary(results)
    print(summary)

    args.out.write_text(
        json.dumps(
            {
                "prompt_version": CURRENT_PROMPT_VERSION,
                "run_at_utc": datetime.now(timezone.utc).isoformat(),
                "timeout_seconds": args.timeout,
                "cases": [asdict(r) for r in results],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"results written to: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
