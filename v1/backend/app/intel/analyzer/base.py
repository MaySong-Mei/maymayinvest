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

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.decision import DecisionDossier, LlmCall
from app.domain.event import Event


# Callback types injected by the caller (typically the pipeline driver).
# Analyzer implementations call these instead of importing persistence /
# brokers / data directly — preserves the analyzer_isolation contract.
SnapshotProvider = Callable[[Event], Awaitable[dict[str, Any]]]
LlmCallRecorder = Callable[[LlmCall], Awaitable[None]]


@dataclass
class AnalyzerContext:
    """What the analyzer is allowed to see during analysis.

    v1 holds this minimal. Expand as analyzers need more capabilities;
    DO NOT bypass ctx (e.g. by importing brokers directly inside an
    analyzer) — that breaks testability AND the audit trail.

    - actor_id identifies which analyzer ran (real CC, stub, etc).
    - snapshot_provider optionally produces the `available_info_snapshot`
      dict for the dossier. If None, analyzer uses {} or the event
      payload alone.
    - record_llm_call optionally persists per-LLM-invocation trace.
      The caller is expected to provide one that writes to llm_calls
      table linked to the dossier_id once the dossier is saved.
      Analyzer that doesn't make LLM calls (e.g. StubAnalyzer) ignores
      this; analyzer that does make calls (ClaudeCodeAnalyzer)
      invokes it when present, no-ops when None.

    The two callbacks are how we hand the analyzer everything it needs
    without breaking the analyzer_isolation import-linter contract
    (analyzer imports only app.domain — never persistence, brokers,
    etc). Concrete implementations live in app.intel.* or the test
    fixture.
    """

    actor_id: str
    snapshot_provider: SnapshotProvider | None = None
    record_llm_call: LlmCallRecorder | None = None
    # Future fields (added when implementations need them):
    # - get_last_price: Callable[[str], Awaitable[Decimal]]
    # - get_recent_bars: Callable[[str, str, int], Awaitable[list[Bar]]]
    # - get_portfolio: Callable[[], Awaitable[Portfolio]]
    # Added lazily so the interface stays small at v1.


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
