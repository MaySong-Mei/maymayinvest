"""DecisionReviewer — the outcome-blind judgment layer.

This is the load-bearing experimental component of v1. Its job: given a
DecisionDossier (and ONLY the dossier — no fills, no future prices, no
P&L), produce a verdict on whether the bet was right at decision time.

PHILOSOPHY.md framing: "right bet, not right gain." The reviewer's
purpose is to evaluate decision quality on a process basis, decoupled
from the noisy outcome.

The whole project's bootstrap depends on whether this layer works.
If reviewer judgments are too noisy, too biased, or too easy for the
operator to game by writing convincing-sounding reasoning, the whole
self-evolving loop becomes a generator of plausible-sounding garbage.
v1 is partly an experiment to find out.

Architectural invariants enforced here (and elsewhere — see
app.persistence.repositories.decisions.build_reviewer_input):

  1. Reviewer input comes EXCLUSIVELY from build_reviewer_input().
     No reviewer implementation reads orders, fills, positions, or
     anything that could carry outcome info. The Protocol's review()
     signature only accepts the reviewer_input dict — there is no
     way to pass in outcomes.

  2. Reviewer prompts are versioned. A reviewer's verdict is paired
     with the prompt version that produced it (DecisionReview.
     reviewer_prompt_version). Comparing reviews across prompt
     versions requires care; prompt evolution is itself a research
     artifact.

  3. Reviewer is NOT on the hot path. Decisions route and execute
     without waiting for a review. Reviews are produced asynchronously
     (background task or batch job). This matters because:
       - Reviewer latency (Claude API call) is 5-30s; can't gate orders
       - Reviewer should not block on errors; failed reviews are
         retried or surfaced as incidents, never block the operator
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.decision import DecisionReview


@dataclass
class ReviewerContext:
    """What the reviewer needs at runtime.

    actor_id identifies WHICH reviewer ran (e.g. "claude-code-reviewer-v1",
    "stub-reviewer", "human-spot-check"). Multiple reviewer types can
    coexist; their judgments are stored side-by-side and can be compared.

    prompt_version identifies which prompt revision the reviewer is using.
    Pinned for a window; rolled forward on deliberate prompt iteration.
    """

    actor_id: str
    prompt_version: str


class DecisionReviewer(Protocol):
    """Outcome-blind reviewer protocol.

    Contract:
      Input:
        - reviewer_input: the dict produced by build_reviewer_input().
          This is the ONLY thing the reviewer receives about the decision.
          Outcome-leak prevention is the caller's responsibility (and is
          structurally enforced by build_reviewer_input).
        - ctx: ReviewerContext (actor_id + prompt_version).

      Output:
        - DecisionReview with decision_id set to reviewer_input["decision_id"]
        - verdict ∈ {right_bet, wrong_bet, ambiguous}
        - reasoning: why
        - flags: structured concerns
        - confidence: reviewer's confidence in its own verdict

      Side effects:
        - MAY write llm_calls rows linked to the review_id. SHOULD NOT
          write the DecisionReview itself — that's the caller's job
          (single write site = single audit point).
        - MUST NOT read orders, fills, positions, market data after the
          decision timestamp, or any other outcome-side-channel info.

      Failure mode:
        - SHOULD raise on transient errors (subprocess timeout, parse
          failure, etc) — caller decides whether to retry or surface
          as incident
        - MUST NOT silently return a default verdict on failure;
          a "right_bet by accident" because of a parse error would
          poison the supervised data
    """

    async def review(
        self,
        reviewer_input: dict[str, Any],
        ctx: ReviewerContext,
    ) -> DecisionReview: ...
