"""DecisionDossier — the central data artifact of the self-evolving system.

Every CC analysis produces one DecisionDossier. The dossier is rich enough
that the reviewer can re-evaluate the decision WITHOUT re-running CC.

Pure domain — no I/O imports. Persistence lives in app.persistence.models;
repositories convert between this domain model and ORM rows.

Invariants:
  - dossier.id and dossier.created_at are immutable once written
  - available_info_snapshot must contain ALL information CC saw at decision time
  - reasoning_chain, alternatives_considered, confidence are CC self-reports
  - skills_invoked references the skill registry by (name, version)
  - llm_call_ids references llm_calls table rows (each prompt/response is captured)
  - outcome fields (filled_price, realized_pnl, etc) are NEVER in the dossier —
    they live in fills/orders/positions and join via decision_id at query time
    but are HIDDEN FROM THE REVIEWER

The last invariant is structural, not just convention: the dossier object
itself does not carry outcome information.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.core.time import utcnow
from app.domain.order import OrderIntent


class DecisionVerdict(StrEnum):
    """Reviewer's judgment on a decision, on information-only basis."""

    RIGHT_BET = "right_bet"
    WRONG_BET = "wrong_bet"
    AMBIGUOUS = "ambiguous"


class SkillInvocation(BaseModel):
    """A single call CC made to a registered skill during analysis."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    args_summary: str = ""  # short text describing what was passed; not full repro


class AlternativeConsidered(BaseModel):
    """An option CC explicitly considered and (usually) rejected."""

    model_config = ConfigDict(frozen=True)

    action: str  # e.g. "hold", "buy small", "buy full size", "sell short"
    rejected_because: str


class ProposedOrder(BaseModel):
    """The order CC proposes, as part of the dossier.

    Lives separately from OrderIntent to keep the dossier domain-pure: the
    dossier records what CC WANTED, even if the order is never submitted
    (notify mode, dry-run, denied at risk gate, etc).
    """

    model_config = ConfigDict(frozen=True)

    intent: OrderIntent | None  # None = explicit "no action" decision
    no_action_reason: str | None = None  # required when intent is None


class DecisionDossier(BaseModel):
    """Central artifact. One per CC analysis run.

    Read by:
      - Reviewer subagent (outcome-blind: ONLY this dossier, no fills/PnL)
      - Skill evolution loop (CC reflects on dossier + paired review)
      - Dashboard (user-facing audit view)
      - Future-self analysis ("why did we do X on date Y")

    The reviewer must be able to judge the decision from this dossier alone.
    If a reviewer would need more info than is here, the dossier is incomplete.
    """

    model_config = ConfigDict(frozen=False)  # Pydantic-mutable; persistence is append-only

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=utcnow)
    actor_id: str  # which CC instance / agent identity made this decision
    actor_type: str = "agent"  # "agent" | "user" (user-driven decisions also get dossiers)

    # What triggered the analysis
    event_id: str | None = None  # references events table once we add it
    event_kind: str  # "edgar_8k", "rss_pr_newswire", "user_initiated", etc
    event_summary: str  # short text: what was the trigger

    # What CC could see at decision time (the reviewer sees ONLY this)
    available_info_snapshot: dict[str, Any] = Field(default_factory=dict)
    # Suggested structure:
    #   {
    #     "event_payload": {...},
    #     "recent_prices": {"AAPL": [...]},
    #     "portfolio": {...},
    #     "news_fetched": [...],
    #     "indicators": {...},
    #     ...
    #   }
    # Free-form for v1 — schema tightens as patterns emerge.

    # CC's reasoning
    reasoning_chain: str  # markdown narrative; this is what reviewer reads first
    alternatives_considered: list[AlternativeConsidered] = Field(default_factory=list)
    confidence: Decimal  # 0.0-1.0; CC's self-assessed confidence
    skills_invoked: list[SkillInvocation] = Field(default_factory=list)

    # The decision itself
    proposed: ProposedOrder

    # Mode and lifecycle
    mode: str = "dry_run"  # "notify" | "dry_run" | "auto"
    latency_ms: int = 0  # end-to-end CC analysis duration

    # Trace
    llm_call_ids: list[UUID] = Field(default_factory=list)  # references llm_calls rows


class DecisionReview(BaseModel):
    """The reviewer subagent's judgment on a DecisionDossier.

    HARD INVARIANT (architectural, not just convention):
      The reviewer is given a DecisionDossier ONLY. The reviewer never sees
      fills, subsequent prices, realized P&L, or any future event.

    Enforcement of outcome-blindness happens in the repository layer
    (build_reviewer_input strips outcome-related fields by construction)
    and is asserted in tests.
    """

    model_config = ConfigDict(frozen=False)

    id: UUID = Field(default_factory=uuid4)
    decision_id: UUID  # FK to dossier
    created_at: datetime = Field(default_factory=utcnow)
    reviewer_id: str  # which reviewer prompt/agent version was used
    reviewer_prompt_version: str  # versioned in skill registry; pinned for a window

    verdict: DecisionVerdict
    reasoning: str  # why the reviewer reached this verdict
    flags: list[str] = Field(default_factory=list)
    # Suggested flag taxonomy:
    #   "considered_too_few_alternatives"
    #   "missed_obvious_downside_catalyst"
    #   "reasoning_doesnt_justify_confidence"
    #   "skills_invoked_inappropriately"
    #   ...

    confidence: Decimal  # reviewer's confidence in its own verdict


class LlmCall(BaseModel):
    """Trace record for a single LLM invocation.

    Captures prompt + response + metadata so:
      - We can replay decisions later
      - We can audit specification gaming attempts
      - We can correlate latency / cost / model with decision quality
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    decision_id: UUID | None = None  # may be None for reviewer calls; reviewer uses review_id
    review_id: UUID | None = None
    created_at: datetime = Field(default_factory=utcnow)
    purpose: str  # "analyze_event", "review_decision", "summarize_news", etc
    model: str  # "claude-opus-4-7", "claude-haiku-4-5", "claude-code", etc
    prompt: str  # the actual prompt sent (may be long; persistence uses Text column)
    response: str  # the actual response received
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error: str | None = None
