"""ClaudeCodeAnalyzer — first real analyzer.

Spawns `claude -p` to produce a DecisionDossier from an Event. Mirrors
the architecture of ClaudeCodeReviewer (same subprocess plumbing, same
versioned prompts, same JSON-strict output) but for the analyzer half
of the pipeline.

Output schema is dossier-shaped; the analyzer is the producer for
DecisionDossier just as the reviewer is the producer for DecisionReview.

This module deliberately does NOT import persistence, brokers, data,
or operator — same isolation as the reviewer. The llm_calls trace is
recorded via the optional `record_llm_call` callback on AnalyzerContext;
the snapshot for the dossier is obtained via the optional
`snapshot_provider` callback. Both default to None for stub-style or
test invocations.

Auth: uses the shared CLAUDE_CODE_OAUTH_TOKEN path (see
app.intel._subprocess._build_subprocess_env). User must have run
`claude setup-token` externally for the OAuth-token path to work.

Failure modes:
  - Subprocess error -> SubprocessError (caller decides retry / incident)
  - JSON parse error -> SubprocessError
  - Output schema doesn't match DecisionDossier expectations ->
    SubprocessError (analyzer must not silently default; bad dossier
    poisons reviewer eval)
"""
from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    LlmCall,
    ProposedOrder,
    SkillInvocation,
)
from app.domain.event import Event
from app.domain.order import OrderIntent, OrderSide, OrderType, TimeInForce
from app.intel._subprocess import (
    DEFAULT_CLAUDE_CMD,
    DEFAULT_TIMEOUT_SECONDS,
    DefaultRunner,
    SubprocessError,
    SubprocessRunner,
    parse_json_strict,
    raise_for_nonzero,
)
from app.intel.analyzer.base import AnalyzerContext, EventAnalyzer
from app.intel.analyzer.prompt import get_prompt


# Re-export for backward-compat (in case other code imports these by name
# from this module rather than the shared module).
__all__ = [
    "ClaudeCodeAnalyzer",
    "AnalyzerError",
]


# Backward-compat alias: tests that import AnalyzerError from this module.
AnalyzerError = SubprocessError


def _parse_dossier_json(raw: str) -> dict[str, Any]:
    """Parse analyzer JSON output with dossier-specific validation."""
    data = parse_json_strict(
        raw,
        required_keys={
            "event_summary",
            "reasoning_chain",
            "alternatives_considered",
            "confidence",
            "skills_invoked",
            "proposed",
            "mode",
        },
    )
    if data["mode"] not in {"notify", "dry_run", "auto"}:
        raise SubprocessError(f"invalid mode: {data['mode']!r}")
    if not isinstance(data["alternatives_considered"], list):
        raise SubprocessError("alternatives_considered must be a list")
    if not isinstance(data["skills_invoked"], list):
        raise SubprocessError("skills_invoked must be a list")
    if not isinstance(data["proposed"], dict):
        raise SubprocessError("proposed must be an object")

    proposed = data["proposed"]
    has_intent = proposed.get("intent") is not None
    has_reason = proposed.get("no_action_reason") is not None
    if has_intent == has_reason:
        raise SubprocessError(
            "proposed must have exactly one of intent or no_action_reason; "
            f"got intent={proposed.get('intent')!r}, "
            f"no_action_reason={proposed.get('no_action_reason')!r}"
        )
    return data


def _intent_from_dict(d: dict[str, Any]) -> OrderIntent:
    """Construct an OrderIntent from analyzer-output JSON. Strict on
    required fields. Defaults: tif=day, type=market."""
    return OrderIntent(
        symbol=str(d["symbol"]),
        side=OrderSide(str(d["side"])),
        qty=Decimal(str(d["qty"])),
        type=OrderType(str(d.get("type", "market"))),
        limit_price=(
            Decimal(str(d["limit_price"]))
            if d.get("limit_price") is not None
            else None
        ),
        tif=TimeInForce(str(d.get("tif", "day"))),
    )


def _proposed_from_dict(d: dict[str, Any]) -> ProposedOrder:
    if d.get("intent") is not None:
        return ProposedOrder(intent=_intent_from_dict(d["intent"]))
    return ProposedOrder(intent=None, no_action_reason=str(d["no_action_reason"]))


class ClaudeCodeAnalyzer(EventAnalyzer):
    """Subprocess-based event analyzer. v1 primary path."""

    def __init__(
        self,
        prompt_version: str = "v1-2026-05-23",
        runner: SubprocessRunner | None = None,
        cmd: tuple[str, ...] = DEFAULT_CLAUDE_CMD,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.prompt_version = prompt_version
        self.runner = runner or DefaultRunner()
        self.cmd = cmd
        self.timeout_seconds = timeout_seconds

    async def analyze(self, event: Event, ctx: AnalyzerContext) -> DecisionDossier:
        # 1. Build event JSON for the prompt
        event_json = json.dumps(
            {
                "kind": event.kind.value,
                "external_id": event.external_id,
                "ts": event.ts.isoformat(),
                "source": event.source,
                "symbols": list(event.symbols),
                "headline": event.headline,
                "payload": event.payload,
            },
            indent=2,
            default=str,
        )

        # 2. Optionally enrich with portfolio / market snapshot
        snapshot: dict[str, Any] = {}
        if ctx.snapshot_provider is not None:
            snapshot = await ctx.snapshot_provider(event)
        snapshot_json = json.dumps(snapshot, indent=2, default=str)

        # 3. Compose the prompt. .replace not .format (template contains
        # literal JSON braces which would trip str.format; see reviewer
        # claude_code.py for the original bug).
        prompt_template = get_prompt(self.prompt_version)
        full_prompt = (
            prompt_template
            .replace("{event_json}", event_json)
            .replace("{snapshot_json}", snapshot_json)
        )

        # 4. Run subprocess and parse
        t0 = time.monotonic()
        result = await self.runner.run(
            cmd=self.cmd,
            stdin=full_prompt,
            timeout_seconds=self.timeout_seconds,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        # 5. Persist llm_call trace if a recorder is provided. Decision_id
        # is generated up front so we can link the trace.
        decision_id = uuid4()
        if ctx.record_llm_call is not None:
            await ctx.record_llm_call(
                LlmCall(
                    decision_id=decision_id,
                    purpose="analyze_event",
                    model="claude-code",
                    prompt=full_prompt,
                    response=result.stdout,
                    latency_ms=elapsed_ms,
                    error=(
                        None
                        if result.returncode == 0
                        else f"exit {result.returncode}; stdout={result.stdout[:200]!r}"
                    ),
                )
            )

        raise_for_nonzero(result)
        data = _parse_dossier_json(result.stdout)

        # 6. Construct DecisionDossier
        alternatives = [
            AlternativeConsidered(
                action=str(a["action"]),
                rejected_because=str(a["rejected_because"]),
            )
            for a in data["alternatives_considered"]
        ]
        skills = [
            SkillInvocation(
                name=str(s.get("name", "unknown")),
                version=str(s.get("version", "0.0.0")),
                args_summary=str(s.get("args_summary", "")),
            )
            for s in data["skills_invoked"]
        ]

        return DecisionDossier(
            id=decision_id,
            actor_id=ctx.actor_id,
            actor_type="agent",
            event_id=event.external_id,
            event_kind=event.kind.value,
            event_summary=str(data["event_summary"]),
            available_info_snapshot=snapshot,
            reasoning_chain=str(data["reasoning_chain"]),
            alternatives_considered=alternatives,
            confidence=Decimal(str(data["confidence"])),
            skills_invoked=skills,
            proposed=_proposed_from_dict(data["proposed"]),
            mode=str(data["mode"]),
            latency_ms=elapsed_ms,
        )


