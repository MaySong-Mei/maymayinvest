"""Shared subprocess plumbing for claude -p invocations.

Both ClaudeCodeAnalyzer and ClaudeCodeReviewer spawn `claude -p` with
a structured prompt and parse JSON output. They share:
  - SubprocessRunner Protocol + _DefaultRunner real implementation
  - SubprocessResult dataclass
  - SubprocessError exception (subprocess failure / timeout)
  - _build_subprocess_env (CLAUDE_CODE_OAUTH_TOKEN handling)
  - _parse_json_strict (markdown-fence tolerance + required-keys check)

What they do NOT share:
  - Prompt content (versioned per-module: analyzer/prompt.py vs reviewer/prompt.py)
  - Output schema (DecisionDossier-shaped vs DecisionReview-shaped)
  - Domain model construction

Lives in app/intel/ rather than app/intel/analyzer/ or app/intel/reviewer/
because it's used by both and is naturally a sibling concern.

Auth discovery history is documented in
v1/docs/evals/reviewer-v1-2026-05-22.md (the `_build_subprocess_env`
three-path design was extracted from there).
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Protocol


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_CLAUDE_CMD = ("claude", "-p", "--output-format", "text")


class SubprocessError(RuntimeError):
    """Subprocess or parse failure. Caller decides retry / incident."""


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

    Three paths, in priority order:

      Path 1 (preferred, subscription users): if
        CLAUDE_CODE_OAUTH_TOKEN is set and non-empty, forward it and
        STRIP ANTHROPIC_API_KEY entirely. ANTHROPIC_API_KEY
        out-precedes OAuth token in claude's auth chain — if a
        poisoned empty ANTHROPIC_API_KEY were left in, it would
        beat the OAuth token and we'd 401.

      Path 2 (API customers): if ANTHROPIC_API_KEY is non-empty,
        leave it alone. claude will use it directly.

      Path 3 (fall-through): strip empty ANTHROPIC_API_KEY and let
        claude try OAuth keychain. This path is known to fail under
        nested Claude Code due to OAuth refresh race (see
        v1/docs/evals/reviewer-v1-2026-05-22.md). Kept only so a
        user running from a fresh terminal can use it without having
        to setup-token.

    Returns the full env dict; caller passes it to subprocess.
    """
    env = dict(os.environ)
    oauth_token = env.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    api_key = env.get("ANTHROPIC_API_KEY", "").strip()

    if oauth_token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
        env.pop("ANTHROPIC_API_KEY", None)
    elif api_key:
        pass
    else:
        env.pop("ANTHROPIC_API_KEY", None)

    return env


class DefaultRunner(SubprocessRunner):
    """Real subprocess runner. Spawns claude -p, pipes prompt on stdin."""

    async def run(
        self,
        cmd: tuple[str, ...],
        stdin: str,
        timeout_seconds: int,
    ) -> SubprocessResult:
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
            raise SubprocessError(
                f"claude subprocess exceeded {timeout_seconds}s timeout"
            ) from exc

        return SubprocessResult(
            returncode=proc.returncode or 0,
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
        )


def parse_json_strict(raw: str, required_keys: set[str]) -> dict[str, Any]:
    """Parse claude's JSON output strictly.

    Tolerates markdown code fences (``` or ```json blocks) because
    real `claude -p` output sometimes wraps despite prompts saying
    "no fences". Beyond that: no leading prose, no trailing prose,
    no partial-object salvage. Parse fails -> SubprocessError.

    required_keys: caller specifies the keys that must be present in
    the parsed object. Missing -> SubprocessError. Extra keys are
    allowed (caller picks the ones it knows).
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SubprocessError(
            f"claude response is not valid JSON: {exc}; raw={raw[:500]!r}"
        ) from exc

    if not isinstance(data, dict):
        raise SubprocessError(
            f"claude response must be a JSON object, got {type(data).__name__}"
        )

    missing = required_keys - data.keys()
    if missing:
        raise SubprocessError(
            f"claude response missing required keys: {sorted(missing)}"
        )

    return data


def raise_for_nonzero(result: SubprocessResult) -> None:
    """Raise SubprocessError if returncode != 0, surfacing both streams.

    The 401-on-stdout finding (2026-05-23) means stderr alone isn't enough
    to diagnose claude auth failures. Both streams are included.
    """
    if result.returncode != 0:
        raise SubprocessError(
            f"claude subprocess exited {result.returncode}; "
            f"stderr={result.stderr[:500]!r}; "
            f"stdout={result.stdout[:500]!r}"
        )
