"""ClaudeCodeReviewer — subprocess to `claude -p` for review.

Stage 0 reviewer implementation. Spawns a non-interactive Claude Code
process with a restricted prompt + the reviewer_input JSON, parses the
JSON response, returns a DecisionReview.

Why subprocess rather than Anthropic SDK directly:
  - PHILOSOPHY.md framing: Claude Code is the operator's body. The
    reviewer is a SEPARATE Claude Code instance with a constrained
    prompt — outcome-blind by construction (it cannot read fills /
    orders because we don't pass them in, and it has no tools that
    let it fetch them).
  - In Stage 2 a ClaudeAPIReviewer can replace this without
    touching the DecisionReviewer protocol.

Failure modes handled:
  - subprocess timeout: TimeoutExpired propagated as ReviewerError
  - non-zero exit: stderr captured into ReviewerError
  - non-JSON response: parse failure raised as ReviewerError
  - malformed JSON (missing required fields): raised as ReviewerError
  - the reviewer MUST NOT silently default; a parse error is preferable
    to a "right_bet by accident" that poisons the supervised dataset

Auth note (final design 2026-05-23, see
v1/docs/evals/reviewer-v1-2026-05-22.md):
The supported auth path for subprocess `claude -p` from a Pro/Max
subscription is `CLAUDE_CODE_OAUTH_TOKEN`, populated by a one-time
`claude setup-token` run by the human in an external terminal.

The default subprocess env is built like this:
  1. If CLAUDE_CODE_OAUTH_TOKEN is set in the parent env: forward it
     to the child, and STRIP ANTHROPIC_API_KEY entirely (it
     out-precedes the OAuth token in claude's auth chain).
  2. Else if ANTHROPIC_API_KEY is non-empty: forward it as-is
     (deliberate user override; behaves like a normal API customer).
  3. Else: strip ANTHROPIC_API_KEY (which is empty-string-poisoned
     by the parent CC session) and forward nothing — falls through
     to OAuth keychain. Known to fail under nested CC due to OAuth
     refresh race; documented but kept as a fall-through path.

Path 1 is the only path that works reliably for subscription users
running this from inside another Claude Code session.

Lifecycle note for path 1:
  - `claude setup-token` mints a token good for ~1 year.
  - Subscription users: usage draws from Pro/Max inference quota
    (no extra billing) for now.
  - Per Anthropic docs (as of 2026-05-23 surveyed by prober
    a1ab74beec13b4b1f): starting 2026-06-15, Agent SDK / `claude -p`
    usage may draw from a separate monthly Agent SDK credit pool.
    Re-check billing model when this date approaches.

Testing: this module is tested with a mocked subprocess runner so unit
tests do not require Claude Code to be installed. The injection point
is `runner` on ClaudeCodeReviewer.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.decision import DecisionReview, DecisionVerdict
from app.intel._subprocess import (
    DEFAULT_CLAUDE_CMD,
    DEFAULT_TIMEOUT_SECONDS,
    DefaultRunner,
    SubprocessError,
    SubprocessResult,
    SubprocessRunner,
    _build_subprocess_env,  # re-exported for backward-compat with tests
    parse_json_strict,
    raise_for_nonzero,
)
from app.intel.reviewer.base import DecisionReviewer, ReviewerContext
from app.intel.reviewer.prompt import get_prompt


# Backward-compatible name. Existing tests import ReviewerError from this
# module; keep that import path alive.
ReviewerError = SubprocessError


# Backward-compatible alias. Tests import _DefaultRunner from here.
_DefaultRunner = DefaultRunner


# Backward-compat re-exports for tests that import these by name from
# app.intel.reviewer.claude_code.
__all__ = [
    "ClaudeCodeReviewer",
    "ReviewerError",
    "SubprocessResult",
    "SubprocessRunner",
    "_DefaultRunner",
    "_build_subprocess_env",
    "_parse_verdict_json",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_CLAUDE_CMD",
]


def _parse_verdict_json(raw: str) -> dict[str, Any]:
    """Parse the reviewer's JSON output (markdown-fence tolerant).

    Wraps the shared parser with reviewer-specific semantic validation:
      - verdict must be one of {right_bet, wrong_bet, ambiguous}
      - flags must be a list
    """
    data = parse_json_strict(
        raw, required_keys={"verdict", "reasoning", "flags", "confidence"}
    )
    if data["verdict"] not in {"right_bet", "wrong_bet", "ambiguous"}:
        raise SubprocessError(f"invalid verdict: {data['verdict']!r}")
    if not isinstance(data["flags"], list):
        raise SubprocessError(
            f"flags must be a list, got {type(data['flags']).__name__}"
        )
    return data


class ClaudeCodeReviewer(DecisionReviewer):
    """Subprocess-based reviewer. v1 primary path."""

    def __init__(
        self,
        runner: SubprocessRunner | None = None,
        cmd: tuple[str, ...] = DEFAULT_CLAUDE_CMD,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.runner = runner or _DefaultRunner()
        self.cmd = cmd
        self.timeout_seconds = timeout_seconds

    async def review(
        self,
        reviewer_input: dict[str, Any],
        ctx: ReviewerContext,
    ) -> DecisionReview:
        decision_id_str = reviewer_input.get("decision_id")
        if not decision_id_str:
            raise ReviewerError("reviewer_input missing decision_id")
        decision_id = UUID(decision_id_str)

        prompt_template = get_prompt(ctx.prompt_version)
        decision_json = json.dumps(reviewer_input, indent=2, default=str)
        # NOTE: .replace not .format. The prompt template contains literal
        # JSON schema (`{"verdict": ...}`) which str.format() would try to
        # interpret as substitution slots. Single-token replacement avoids
        # that. If a future prompt needs multiple slots, switch to
        # string.Template or a Jinja-style escape.
        full_prompt = prompt_template.replace("{decision_json}", decision_json)

        result = await self.runner.run(
            cmd=self.cmd,
            stdin=full_prompt,
            timeout_seconds=self.timeout_seconds,
        )
        raise_for_nonzero(result)
        data = _parse_verdict_json(result.stdout)

        return DecisionReview(
            decision_id=decision_id,
            reviewer_id=ctx.actor_id,
            reviewer_prompt_version=ctx.prompt_version,
            verdict=DecisionVerdict(data["verdict"]),
            reasoning=str(data["reasoning"]),
            flags=[str(f) for f in data["flags"]],
            confidence=Decimal(str(data["confidence"])),
        )


