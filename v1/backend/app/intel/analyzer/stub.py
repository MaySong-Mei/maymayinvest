"""StubAnalyzer — deterministic, no-LLM implementation of EventAnalyzer.

Purpose:
  - Wire the pipeline end-to-end without depending on a live LLM
  - Test downstream code (reviewer, mode routing, persistence)
  - Serve as the contract reference: any real analyzer must produce a
    DecisionDossier with at least these fields populated

Behavior:
  - Reads the event headline + symbols
  - Produces a no-action dossier with a fixed reasoning string
  - Confidence = 0.5 (it's a stub; signals nothing)
  - Latency = constant
  - mode = "notify" (stub never proposes orders)

Real analyzers replace this. They do NOT inherit from it.
"""
from __future__ import annotations

from decimal import Decimal

from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    ProposedOrder,
)
from app.domain.event import Event
from app.intel.analyzer.base import AnalyzerContext, EventAnalyzer


class StubAnalyzer(EventAnalyzer):
    """Deterministic stub. Used in tests and dev plumbing."""

    async def analyze(self, event: Event, ctx: AnalyzerContext) -> DecisionDossier:
        primary_symbol = event.symbols[0] if event.symbols else "UNKNOWN"
        return DecisionDossier(
            actor_id=ctx.actor_id,
            actor_type="agent",
            event_id=event.external_id,
            event_kind=event.kind.value,
            event_summary=event.headline,
            available_info_snapshot={
                "event_payload": event.payload,
                "symbols": list(event.symbols),
            },
            reasoning_chain=(
                f"[stub-analyzer] Event {event.kind.value} on {primary_symbol}. "
                "No real analysis performed; this is a deterministic stub used "
                "to wire the pipeline end-to-end."
            ),
            alternatives_considered=[
                AlternativeConsidered(
                    action="no_action",
                    rejected_because="stub does not propose orders",
                ),
            ],
            confidence=Decimal("0.5"),
            skills_invoked=[],
            proposed=ProposedOrder(
                intent=None,
                no_action_reason="stub analyzer never proposes orders",
            ),
            mode="notify",
            latency_ms=0,
        )
