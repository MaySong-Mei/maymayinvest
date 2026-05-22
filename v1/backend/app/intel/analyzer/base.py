"""EventAnalyzer — the swap point between CC and any future replacement.

The analyzer reads an Event and produces a DecisionDossier. v1's primary
implementation is ClaudeCodeAnalyzer (subprocess-based, slow but rich).
Future implementations (e.g. ClaudeAPIAnalyzer for cloud deploy) plug in
at this same interface.

Everything downstream of EventAnalyzer.analyze() is implementation-
agnostic: reviewer, mode routing, persistence, dashboard. This is the
most important contract in v1.

AnalyzerContext carries the read-side capabilities the analyzer is
allowed to use during analysis. Implementations should access broker /
market data / portfolio only through ctx, never directly — this is what
makes the analyzer testable with a stub.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.decision import DecisionDossier
from app.domain.event import Event


@dataclass
class AnalyzerContext:
    """What the analyzer is allowed to see during analysis.

    v1 holds this minimal. Expand as analyzers need more capabilities;
    DO NOT bypass ctx (e.g. by importing brokers directly inside an
    analyzer) — that breaks testability AND the audit trail.
    """

    actor_id: str  # e.g. "claude-code-instance-1" or "stub-analyzer"
    # Future fields (added when implementations need them):
    # - get_last_price: Callable[[str], Awaitable[Decimal]]
    # - get_recent_bars: Callable[[str, str, int], Awaitable[list[Bar]]]
    # - get_portfolio: Callable[[], Awaitable[Portfolio]]
    # These are added lazily so the interface stays small at v1.


class EventAnalyzer(Protocol):
    """Analyzer protocol.

    Implementations:
      - StubAnalyzer (deterministic, no LLM; for tests and dev plumbing)
      - ClaudeCodeAnalyzer (subprocess to `claude -p`; v1 primary path)
      - ClaudeAPIAnalyzer (direct anthropic SDK; Stage 2 cloud variant)

    Contract:
      - Input: Event + AnalyzerContext
      - Output: DecisionDossier (with event_id set to Event.external_id)
      - Side effects: implementations may write llm_calls rows linked to
        the dossier, but MUST NOT write the dossier itself — the caller
        does that via save_dossier, so the lifecycle (and audit) is
        owned by a single place.
      - Determinism: not required; the stub is deterministic, real CC
        is not. Tests against real CC must not assert exact dossier
        contents — only contract-level properties (required fields
        present, intent well-formed, confidence in [0,1], etc).
      - Failure: implementations should raise; never silently return a
        "failed" dossier. The caller handles incidents.
    """

    async def analyze(self, event: Event, ctx: AnalyzerContext) -> DecisionDossier:
        ...
