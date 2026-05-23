"""Goal state machine: case-3 multi-attempt consistency check.

First-attempt eval (commit 6542ea3) showed reviewer disagreeing with the
operator's `ambiguous` label on case-3, verdicting `right_bet` with a
substantive argument. Per PHILOSOPHY.md "Goal state machine":
  - one disagreement is not yet evidence the goal (label) is wrong
  - attempts < 3 + cost < cap permit silent retry

This script runs case-3 twice more (attempts 2 and 3) to see whether the
reviewer's verdict is stable. Outcomes:

  - all 3 attempts judge right_bet with similar reasoning
    => stronger evidence that the operator's label is the issue.
       Eligible (but not required) to open a dialogue-reviewer
       conversation and consider a `proposals/` entry.

  - verdict varies (e.g. one ambiguous, one right_bet, one wrong_bet)
    => reviewer noise is the issue; the operator's label may be fine.
       Different intervention needed (multi-reviewer ensembling? prompt
       tighten? prompt v2 proposal).

Run from v1/backend with CLAUDE_CODE_OAUTH_TOKEN set in env.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Path: scripts/ is sibling to app/
_REPO_BACKEND = Path(__file__).resolve().parent.parent
if str(_REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(_REPO_BACKEND))

from app.intel.reviewer.claude_code import ClaudeCodeReviewer  # noqa: E402
from app.intel.reviewer.base import ReviewerContext  # noqa: E402
from app.intel.reviewer.prompt import CURRENT_PROMPT_VERSION  # noqa: E402
from scripts.eval_reviewer import _build_reviewer_input_from_dossier  # noqa: E402
from tests.eval.reviewer_eval_set import ALL_CASES  # noqa: E402


CASE_NAME = "case-3-sound-no-action-under-ambiguity"
# Pre-2026-05-23-relabel name was "case-3-legitimately-ambiguous".
# Historical JSON files (e.g. reviewer-v1-2026-05-22-case3-consistency-2026-05-23.json)
# still reference the old name as the case_name they were run against —
# that's a snapshot of the past, do not retroactively change it.
N_ATTEMPTS = 2  # attempts 2 and 3; attempt 1 already in main eval


async def main() -> int:
    case = next(c for c in ALL_CASES if c.name == CASE_NAME)
    reviewer_input = _build_reviewer_input_from_dossier(case)
    reviewer = ClaudeCodeReviewer(timeout_seconds=240)

    print(
        f"goal state machine: case-3 multi-attempt consistency check\n"
        f"  prompt version: {CURRENT_PROMPT_VERSION}\n"
        f"  attempts this session: {N_ATTEMPTS} (attempts 2 and 3; attempt 1 in main eval)\n"
    )

    results = []
    for i in range(N_ATTEMPTS):
        attempt_no = i + 2  # attempts 2 and 3
        ctx = ReviewerContext(
            actor_id=f"case3-consistency-attempt-{attempt_no}",
            prompt_version=CURRENT_PROMPT_VERSION,
        )
        print(f"  -> attempt {attempt_no} ... ", end="", flush=True)
        t0 = time.monotonic()
        try:
            review = await reviewer.review(reviewer_input, ctx)
        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - t0
            print(f"ERROR ({elapsed:.1f}s): {type(exc).__name__}: {exc}")
            results.append({
                "attempt": attempt_no,
                "error": f"{type(exc).__name__}: {exc}",
                "latency_seconds": elapsed,
            })
            continue
        elapsed = time.monotonic() - t0
        print(f"{review.verdict.value} (conf {review.confidence}, {elapsed:.1f}s)")
        results.append({
            "attempt": attempt_no,
            "verdict": review.verdict.value,
            "confidence": float(review.confidence),
            "flags": list(review.flags),
            "reasoning": review.reasoning,
            "latency_seconds": elapsed,
        })

    out_dir = _REPO_BACKEND.parent / "docs" / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / f"reviewer-{CURRENT_PROMPT_VERSION}-case3-consistency-{today}.json"
    out_path.write_text(
        json.dumps(
            {
                "case_name": CASE_NAME,
                "prompt_version": CURRENT_PROMPT_VERSION,
                "run_at_utc": datetime.now(timezone.utc).isoformat(),
                "results": results,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nwritten to: {out_path}")

    # Summary
    print("\n--- summary ---")
    verdicts = [r.get("verdict", "ERROR") for r in results]
    print(f"  attempt 1 (from main eval): right_bet")
    for r in results:
        v = r.get("verdict", f"ERROR: {r.get('error', '')[:60]}")
        c = r.get("confidence", "—")
        print(f"  attempt {r['attempt']}: {v} (conf {c})")

    all_verdicts = ["right_bet"] + verdicts  # include attempt 1
    if all(v == "right_bet" for v in all_verdicts if v != "ERROR"):
        print("\n  3-attempt consistency: STABLE on right_bet")
        print("  Per state machine: this strengthens the case that operator's")
        print("  `ambiguous` label is the candidate for revision. NOT yet")
        print("  sufficient by itself — operator should reflect on the")
        print("  reviewer's reasoning and only file a proposal if it agrees.")
    else:
        print("\n  3-attempt consistency: VARIES")
        print("  Reviewer noise is the candidate issue, not the operator's label.")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
