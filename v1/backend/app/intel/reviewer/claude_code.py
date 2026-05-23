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

Auth note (discovered 2026-05-23, see
v1/docs/evals/reviewer-v1-2026-05-22.md):
When this code runs from inside a Claude Code session, the parent
process exports `ANTHROPIC_API_KEY=` (empty string) in its env.
The child subprocess inherits that empty value, and claude's auth
chain prioritizes ANTHROPIC_API_KEY over OAuth keychain — sending
an empty bearer token to the API and getting 401. The default
runner scrubs that empty value so OAuth keychain auth (from
~/.claude/.credentials.json) takes precedence. Explicit non-empty
ANTHROPIC_API_KEY is preserved (it's a deliberate override).

Testing: this module is tested with a mocked subprocess runner so unit
tests do not require Claude Code to be installed. The injection point
is `runner` on ClaudeCodeReviewer.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.domain.decision import DecisionReview, DecisionVerdict
from app.intel.reviewer.base import DecisionReviewer, ReviewerContext
from app.intel.reviewer.prompt import get_prompt


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_CLAUDE_CMD = ("claude", "-p", "--output-format", "text")


class ReviewerError(RuntimeError):
    """Reviewer subprocess or parse failure. Caller decides retry / incident."""


@dataclass
class SubprocessResult:
    """What a runner returns. Mirrors subprocess.CompletedProcess just enough
    to keep tests from depending on the stdlib type."""

    returncode: int
    stdout: str
    stderr: str


class SubprocessRunner(Protocol):
    """Injection point. Default impl shells out to `claude -p`; tests pass
    a fake runner that returns a canned SubprocessResult."""

    async def run(
        self,
        cmd: tuple[str, ...],
        stdin: str,
        timeout_seconds: int,
    ) -> SubprocessResult: ...


def _build_subprocess_env() -> dict[str, str]:
    """Construct the env passed to the claude subprocess.

    Critical: scrub `ANTHROPIC_API_KEY` if and only if it is the empty
    string. The Claude Code parent process exports `ANTHROPIC_API_KEY=`
    (empty) into its env, presumably as a marker. Children that
    blindly inherit it send "" as a bearer token to the API and get 401.

    We:
      - keep ANTHROPIC_API_KEY if it has a real (non-empty) value
        (explicit user override)
      - drop ANTHROPIC_API_KEY if it's empty or whitespace-only
        (the poison case)
      - leave everything else alone

    OAuth keychain auth via ~/.claude/.credentials.json takes over when
    ANTHROPIC_API_KEY is absent, which is what we want for Pro/Max
    subscription users running this from inside a Claude Code session.
    """
    env = dict(os.environ)
    val = env.get("ANTHROPIC_API_KEY", "").strip()
    if not val:
        env.pop("ANTHROPIC_API_KEY", None)
    return env


class _DefaultRunner(SubprocessRunner):
    """Real subprocess runner. Spawns claude -p, pipes prompt on stdin."""

    async def run(
        self,
        cmd: tuple[str, ...],
        stdin: str,
        timeout_seconds: int,
    ) -> SubprocessResult:
        # asyncio.subprocess so we don't block the event loop
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_build_subprocess_env(),
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(stdin.encode("utf-8")),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise ReviewerError(
                f"claude subprocess exceeded {timeout_seconds}s timeout"
            ) from exc

        return SubprocessResult(
            returncode=proc.returncode or 0,
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
        )


def _parse_verdict_json(raw: str) -> dict[str, Any]:
    """Parse the reviewer's JSON output. Strict — no markdown fence
    tolerance, no leading prose. The prompt instructs JSON-only.

    Real claude -p output sometimes wraps in ```json fences. We strip
    those defensively since prompt obedience is not 100%.
    """
    text = raw.strip()
    if text.startswith("```"):
        # strip ```json ... ``` or ``` ... ```
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReviewerError(f"reviewer response is not valid JSON: {exc}; raw={raw!r}") from exc

    if not isinstance(data, dict):
        raise ReviewerError(f"reviewer response must be a JSON object, got {type(data).__name__}")

    required = {"verdict", "reasoning", "flags", "confidence"}
    missing = required - data.keys()
    if missing:
        raise ReviewerError(f"reviewer response missing required keys: {sorted(missing)}")

    if data["verdict"] not in {"right_bet", "wrong_bet", "ambiguous"}:
        raise ReviewerError(f"invalid verdict: {data['verdict']!r}")

    if not isinstance(data["flags"], list):
        raise ReviewerError(f"flags must be a list, got {type(data['flags']).__name__}")

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

        if result.returncode != 0:
            # Some claude failures (notably 401 auth errors) write the
            # diagnostic to stdout rather than stderr. Include both streams
            # in the error so the cause isn't lost. Found during the
            # 2026-05-23 reviewer eval — see v1/docs/evals/reviewer-v1-2026-05-22.md.
            raise ReviewerError(
                f"claude subprocess exited {result.returncode}; "
                f"stderr={result.stderr[:500]!r}; "
                f"stdout={result.stdout[:500]!r}"
            )

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


# expose for test injection
_ = subprocess  # keep import in case _DefaultRunner gets a sync fallback later
