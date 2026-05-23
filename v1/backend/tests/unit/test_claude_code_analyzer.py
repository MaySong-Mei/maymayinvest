"""ClaudeCodeAnalyzer tests (subprocess mocked).

Critical invariants:
  - Happy path: subprocess output -> well-formed DecisionDossier with all
    domain fields populated correctly
  - Subprocess error -> SubprocessError (no silent default dossier)
  - Parse error -> SubprocessError
  - Schema validation: invalid mode / non-list alternatives / both intent
    AND no_action_reason set -> SubprocessError
  - llm_call recorder is invoked when ctx.record_llm_call is set
  - snapshot_provider populates dossier.available_info_snapshot
  - event_id round-trips from event.external_id to dossier.event_id
  - actor_id round-trips from ctx.actor_id to dossier.actor_id
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.decision import DecisionDossier, LlmCall
from app.domain.event import Event, EventKind
from app.intel._subprocess import (
    SubprocessError,
    SubprocessResult,
    SubprocessRunner,
)
from app.intel.analyzer.base import AnalyzerContext
from app.intel.analyzer.claude_code import (
    ClaudeCodeAnalyzer,
    _parse_dossier_json,
)


class _FakeRunner(SubprocessRunner):
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[tuple] = []

    async def run(self, cmd, stdin, timeout_seconds):
        self.calls.append((cmd, stdin, timeout_seconds))
        return SubprocessResult(
            returncode=self.returncode, stdout=self.stdout, stderr=self.stderr
        )


def _event() -> Event:
    return Event(
        kind=EventKind.EDGAR_8K,
        external_id="manual:aapl-2024-buyback",
        ts=datetime(2024, 5, 2, 20, 30, tzinfo=UTC),
        source="manual",
        symbols=["AAPL"],
        headline="Apple announces buyback program",
        payload={"form_type": "8-K"},
    )


_VALID_DOSSIER_JSON = """\
{
  "event_summary": "Apple announces $110B buyback + dividend hike",
  "reasoning_chain": "Large structural supply-reduction event. Right-side approach is to wait for next-session open confirmation rather than chase the after-hours move, but a partial position now captures some of the structural bullishness.",
  "alternatives_considered": [
    {"action": "hold", "rejected_because": "structural signal too strong to ignore"},
    {"action": "buy full size", "rejected_because": "extended-hours liquidity poor; partial-now-add-on-confirm is right-side"}
  ],
  "confidence": 0.7,
  "skills_invoked": [
    {"name": "buyback_base_rate", "version": "0.1.0", "args_summary": "ticker=AAPL"}
  ],
  "proposed": {
    "intent": {
      "symbol": "AAPL",
      "side": "buy",
      "qty": "2",
      "type": "market",
      "limit_price": null,
      "tif": "day"
    },
    "no_action_reason": null
  },
  "mode": "dry_run"
}
"""


# ---------- happy path ----------


@pytest.mark.asyncio
async def test_happy_path_produces_well_formed_dossier():
    runner = _FakeRunner(stdout=_VALID_DOSSIER_JSON)
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test-cc-analyzer-1")

    dossier = await analyzer.analyze(_event(), ctx)

    assert isinstance(dossier, DecisionDossier)
    assert dossier.event_id == "manual:aapl-2024-buyback"
    assert dossier.event_kind == "edgar_8k"
    assert dossier.actor_id == "test-cc-analyzer-1"
    assert dossier.actor_type == "agent"
    assert "buyback" in dossier.event_summary.lower()
    assert "structural" in dossier.reasoning_chain.lower()
    assert len(dossier.alternatives_considered) == 2
    assert dossier.alternatives_considered[0].action == "hold"
    assert len(dossier.skills_invoked) == 1
    assert dossier.skills_invoked[0].name == "buyback_base_rate"
    assert dossier.proposed.intent is not None
    assert dossier.proposed.intent.symbol == "AAPL"
    assert dossier.proposed.intent.qty == Decimal("2")
    assert dossier.proposed.no_action_reason is None
    assert dossier.confidence == Decimal("0.7")
    assert dossier.mode == "dry_run"
    assert dossier.latency_ms >= 0


@pytest.mark.asyncio
async def test_no_action_dossier_round_trip():
    no_action_json = """{
      "event_summary": "ambiguous CEO departure",
      "reasoning_chain": "info insufficient",
      "alternatives_considered": [{"action": "probe", "rejected_because": "attention cost"}],
      "confidence": 0.5,
      "skills_invoked": [],
      "proposed": {"intent": null, "no_action_reason": "info insufficient"},
      "mode": "notify"
    }"""
    runner = _FakeRunner(stdout=no_action_json)
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test-cc-analyzer-1")

    dossier = await analyzer.analyze(_event(), ctx)
    assert dossier.proposed.intent is None
    assert dossier.proposed.no_action_reason == "info insufficient"
    assert dossier.mode == "notify"


# ---------- snapshot_provider callback ----------


@pytest.mark.asyncio
async def test_snapshot_provider_populates_snapshot():
    captured: dict = {}

    async def provider(event):
        captured["event_id"] = event.external_id
        return {"portfolio": {"cash": "98000"}, "recent_prices": {"AAPL": [220.0]}}

    runner = _FakeRunner(stdout=_VALID_DOSSIER_JSON)
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test", snapshot_provider=provider)

    dossier = await analyzer.analyze(_event(), ctx)
    assert dossier.available_info_snapshot == {
        "portfolio": {"cash": "98000"},
        "recent_prices": {"AAPL": [220.0]},
    }
    assert captured["event_id"] == "manual:aapl-2024-buyback"


@pytest.mark.asyncio
async def test_no_snapshot_provider_means_empty_snapshot():
    runner = _FakeRunner(stdout=_VALID_DOSSIER_JSON)
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test")
    dossier = await analyzer.analyze(_event(), ctx)
    assert dossier.available_info_snapshot == {}


# ---------- llm_call recorder callback ----------


@pytest.mark.asyncio
async def test_llm_call_recorder_invoked_with_trace():
    recorded: list[LlmCall] = []

    async def recorder(call):
        recorded.append(call)

    runner = _FakeRunner(stdout=_VALID_DOSSIER_JSON)
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test", record_llm_call=recorder)

    dossier = await analyzer.analyze(_event(), ctx)
    assert len(recorded) == 1
    call = recorded[0]
    assert call.decision_id == dossier.id
    assert call.purpose == "analyze_event"
    assert call.model == "claude-code"
    assert call.response == _VALID_DOSSIER_JSON
    assert call.error is None


# ---------- error paths ----------


@pytest.mark.asyncio
async def test_subprocess_nonzero_raises():
    runner = _FakeRunner(stdout="", returncode=1, stderr="boom")
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test")
    with pytest.raises(SubprocessError, match="exited 1"):
        await analyzer.analyze(_event(), ctx)


@pytest.mark.asyncio
async def test_subprocess_nonzero_still_records_llm_call_with_error():
    """When subprocess fails, the llm_call trace should still be recorded
    with the error so we have audit visibility into failed runs."""
    recorded: list[LlmCall] = []

    async def recorder(call):
        recorded.append(call)

    runner = _FakeRunner(stdout="some stdout", returncode=1, stderr="some stderr")
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test", record_llm_call=recorder)

    with pytest.raises(SubprocessError):
        await analyzer.analyze(_event(), ctx)

    assert len(recorded) == 1
    assert recorded[0].error is not None
    assert "exit 1" in recorded[0].error


@pytest.mark.asyncio
async def test_parse_failure_raises():
    runner = _FakeRunner(stdout="not json at all")
    analyzer = ClaudeCodeAnalyzer(runner=runner)
    ctx = AnalyzerContext(actor_id="test")
    with pytest.raises(SubprocessError, match="not valid JSON"):
        await analyzer.analyze(_event(), ctx)


# ---------- schema validation in _parse_dossier_json ----------


def test_parser_rejects_invalid_mode():
    raw = """{
      "event_summary": "x",
      "reasoning_chain": "x",
      "alternatives_considered": [],
      "confidence": 0.5,
      "skills_invoked": [],
      "proposed": {"intent": null, "no_action_reason": "x"},
      "mode": "totally-made-up"
    }"""
    with pytest.raises(SubprocessError, match="invalid mode"):
        _parse_dossier_json(raw)


def test_parser_rejects_proposed_with_both_intent_and_reason():
    raw = """{
      "event_summary": "x",
      "reasoning_chain": "x",
      "alternatives_considered": [],
      "confidence": 0.5,
      "skills_invoked": [],
      "proposed": {"intent": {"symbol": "AAPL", "side": "buy", "qty": "1"}, "no_action_reason": "x"},
      "mode": "dry_run"
    }"""
    with pytest.raises(SubprocessError, match="exactly one"):
        _parse_dossier_json(raw)


def test_parser_rejects_proposed_with_neither():
    raw = """{
      "event_summary": "x",
      "reasoning_chain": "x",
      "alternatives_considered": [],
      "confidence": 0.5,
      "skills_invoked": [],
      "proposed": {"intent": null, "no_action_reason": null},
      "mode": "dry_run"
    }"""
    with pytest.raises(SubprocessError, match="exactly one"):
        _parse_dossier_json(raw)


def test_parser_rejects_non_list_alternatives():
    raw = """{
      "event_summary": "x",
      "reasoning_chain": "x",
      "alternatives_considered": "should be a list",
      "confidence": 0.5,
      "skills_invoked": [],
      "proposed": {"intent": null, "no_action_reason": "x"},
      "mode": "dry_run"
    }"""
    with pytest.raises(SubprocessError, match="alternatives_considered must be a list"):
        _parse_dossier_json(raw)


def test_parser_accepts_markdown_fence_wrapped():
    raw = "```json\n" + _VALID_DOSSIER_JSON + "\n```"
    data = _parse_dossier_json(raw)
    assert data["mode"] == "dry_run"


def test_parser_missing_required_key():
    # confidence missing
    raw = """{
      "event_summary": "x",
      "reasoning_chain": "x",
      "alternatives_considered": [],
      "skills_invoked": [],
      "proposed": {"intent": null, "no_action_reason": "x"},
      "mode": "dry_run"
    }"""
    with pytest.raises(SubprocessError, match="missing required keys"):
        _parse_dossier_json(raw)
