"""Reviewer protocol + ClaudeCodeReviewer + review_pipeline tests.

Critical invariants:
  - Reviewer receives ONLY the outcome-blind reviewer_input dict
    (cannot read fills/orders/positions directly)
  - JSON parse is strict: malformed -> ReviewerError, never default verdict
  - Stub always returns ambiguous (deterministic; safe pipeline wiring)
  - review_pipeline persists exactly one Review row per call
  - reviewer_prompt_version is round-tripped from ctx -> review row
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    DecisionVerdict,
    ProposedOrder,
)
from app.intel.review_pipeline import review_decision
from app.intel.reviewer.base import ReviewerContext
from app.intel.reviewer.claude_code import (
    ClaudeCodeReviewer,
    ReviewerError,
    SubprocessResult,
    SubprocessRunner,
    _build_subprocess_env,
    _parse_verdict_json,
)
from app.intel.reviewer.stub import StubReviewer
from app.persistence.models import Base, Review
from app.persistence.repositories.decisions import save_dossier


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        yield s
    await engine.dispose()


async def _seed_dossier(session) -> DecisionDossier:
    dossier = DecisionDossier(
        actor_id="test-operator",
        event_id="test:abc",
        event_kind="test_synthetic",
        event_summary="test event",
        available_info_snapshot={"event_payload": {"x": 1}},
        reasoning_chain="reasoning text",
        alternatives_considered=[
            AlternativeConsidered(action="hold", rejected_because="x"),
        ],
        confidence=Decimal("0.6"),
        skills_invoked=[],
        proposed=ProposedOrder(intent=None, no_action_reason="t"),
        mode="notify",
    )
    await save_dossier(session, dossier)
    return dossier


# ---------- Stub reviewer ----------


@pytest.mark.asyncio
async def test_stub_reviewer_returns_ambiguous(session):
    dossier = await _seed_dossier(session)
    reviewer_input = {"decision_id": str(dossier.id)}
    reviewer = StubReviewer()
    ctx = ReviewerContext(actor_id="stub-test", prompt_version="v1-2026-05-22")
    review = await reviewer.review(reviewer_input, ctx)

    assert review.verdict == DecisionVerdict.AMBIGUOUS
    assert review.decision_id == dossier.id
    assert review.reviewer_id == "stub-test"
    assert "stub-reviewer-no-real-judgment" in review.flags


# ---------- ClaudeCodeReviewer: JSON parser ----------


def test_parse_valid_json():
    raw = '{"verdict": "right_bet", "reasoning": "ok", "flags": [], "confidence": 0.8}'
    data = _parse_verdict_json(raw)
    assert data["verdict"] == "right_bet"
    assert data["confidence"] == 0.8


def test_parse_strips_markdown_code_fence():
    raw = (
        '```json\n'
        '{"verdict": "wrong_bet", "reasoning": "x", "flags": ["a"], "confidence": 0.5}\n'
        '```'
    )
    data = _parse_verdict_json(raw)
    assert data["verdict"] == "wrong_bet"


def test_parse_rejects_invalid_json():
    with pytest.raises(ReviewerError, match="not valid JSON"):
        _parse_verdict_json("not json at all")


def test_parse_rejects_non_object():
    with pytest.raises(ReviewerError, match="must be a JSON object"):
        _parse_verdict_json('["array", "not", "object"]')


def test_parse_rejects_missing_keys():
    raw = '{"verdict": "right_bet", "reasoning": "x"}'  # missing flags, confidence
    with pytest.raises(ReviewerError, match="missing required keys"):
        _parse_verdict_json(raw)


def test_parse_rejects_invalid_verdict():
    raw = '{"verdict": "maybe", "reasoning": "x", "flags": [], "confidence": 0.5}'
    with pytest.raises(ReviewerError, match="invalid verdict"):
        _parse_verdict_json(raw)


def test_parse_rejects_non_list_flags():
    raw = '{"verdict": "right_bet", "reasoning": "x", "flags": "a", "confidence": 0.5}'
    with pytest.raises(ReviewerError, match="flags must be a list"):
        _parse_verdict_json(raw)


# ---------- ClaudeCodeReviewer: subprocess integration via mock ----------


class _FakeRunner(SubprocessRunner):
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[tuple] = []

    async def run(self, cmd, stdin, timeout_seconds):
        self.calls.append((cmd, stdin, timeout_seconds))
        return SubprocessResult(
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
        )


@pytest.mark.asyncio
async def test_claude_code_reviewer_happy_path(session):
    dossier = await _seed_dossier(session)
    fake_stdout = (
        '{"verdict": "right_bet", "reasoning": "process sound", '
        '"flags": ["considered_too_few_alternatives"], "confidence": 0.75}'
    )
    reviewer = ClaudeCodeReviewer(runner=_FakeRunner(stdout=fake_stdout))
    ctx = ReviewerContext(actor_id="cc-reviewer-1", prompt_version="v1-2026-05-22")

    reviewer_input = {
        "decision_id": str(dossier.id),
        "event_summary": "test",
        "reasoning_chain": "r",
    }
    review = await reviewer.review(reviewer_input, ctx)

    assert review.verdict == DecisionVerdict.RIGHT_BET
    assert review.decision_id == dossier.id
    assert review.reviewer_id == "cc-reviewer-1"
    assert review.reviewer_prompt_version == "v1-2026-05-22"
    assert review.flags == ["considered_too_few_alternatives"]
    assert review.confidence == Decimal("0.75")


@pytest.mark.asyncio
async def test_claude_code_reviewer_propagates_subprocess_error():
    runner = _FakeRunner(stdout="", returncode=2, stderr="claude: not authenticated")
    reviewer = ClaudeCodeReviewer(runner=runner)
    ctx = ReviewerContext(actor_id="cc-reviewer-1", prompt_version="v1-2026-05-22")
    with pytest.raises(ReviewerError, match="exited 2"):
        await reviewer.review({"decision_id": str(uuid4())}, ctx)


@pytest.mark.asyncio
async def test_claude_code_reviewer_raises_on_parse_failure():
    runner = _FakeRunner(stdout="this is not json")
    reviewer = ClaudeCodeReviewer(runner=runner)
    ctx = ReviewerContext(actor_id="cc-reviewer-1", prompt_version="v1-2026-05-22")
    with pytest.raises(ReviewerError, match="not valid JSON"):
        await reviewer.review({"decision_id": str(uuid4())}, ctx)


@pytest.mark.asyncio
async def test_claude_code_reviewer_rejects_unknown_prompt_version():
    runner = _FakeRunner(stdout="{}")
    reviewer = ClaudeCodeReviewer(runner=runner)
    ctx = ReviewerContext(actor_id="cc-reviewer-1", prompt_version="v999-nonexistent")
    with pytest.raises(KeyError, match="not registered"):
        await reviewer.review({"decision_id": str(uuid4())}, ctx)


# ---------- review_pipeline integration ----------


@pytest.mark.asyncio
async def test_review_pipeline_persists_review(session):
    dossier = await _seed_dossier(session)
    reviewer = StubReviewer()
    ctx = ReviewerContext(actor_id="stub-pipeline-test", prompt_version="v1-2026-05-22")

    review = await review_decision(session, reviewer, dossier.id, ctx)

    # returned object
    assert review.decision_id == dossier.id
    assert review.verdict == DecisionVerdict.AMBIGUOUS

    # persisted row
    rows = (await session.execute(select(Review))).scalars().all()
    assert len(rows) == 1
    assert rows[0].decision_id == dossier.id
    assert rows[0].verdict == "ambiguous"


@pytest.mark.asyncio
async def test_review_pipeline_supports_multiple_reviewers_per_decision(session):
    """A decision can be reviewed by multiple reviewers (different actor_id
    or different prompt_version) — by design."""
    dossier = await _seed_dossier(session)
    reviewer = StubReviewer()

    ctx_a = ReviewerContext(actor_id="reviewer-a", prompt_version="v1-2026-05-22")
    ctx_b = ReviewerContext(actor_id="reviewer-b", prompt_version="v1-2026-05-22")

    await review_decision(session, reviewer, dossier.id, ctx_a)
    await review_decision(session, reviewer, dossier.id, ctx_b)

    rows = (await session.execute(select(Review))).scalars().all()
    assert len(rows) == 2
    assert sorted(r.reviewer_id for r in rows) == ["reviewer-a", "reviewer-b"]


@pytest.mark.asyncio
async def test_review_pipeline_outcome_blind(session):
    """review_decision passes the build_reviewer_input output to the reviewer.

    If the reviewer ever received outcome-leak fields, this test would
    catch it via a custom reviewer that inspects what it got.
    """
    dossier = DecisionDossier(
        actor_id="test-operator",
        event_id="test:leak-attempt",
        event_kind="test_synthetic",
        event_summary="test",
        available_info_snapshot={
            "event_payload": {"x": 1},
            # Outcome-leak fields seeded directly into snapshot:
            "realized_pnl": "999",
            "filled_price": "123.45",
            "outcome": "won",
        },
        reasoning_chain="r",
        alternatives_considered=[
            AlternativeConsidered(action="hold", rejected_because="x"),
        ],
        confidence=Decimal("0.5"),
        skills_invoked=[],
        proposed=ProposedOrder(intent=None, no_action_reason="t"),
        mode="notify",
    )
    await save_dossier(session, dossier)

    received_inputs: list[dict] = []

    class _InspectorReviewer:
        async def review(self, reviewer_input, ctx):
            received_inputs.append(reviewer_input)
            return await StubReviewer().review(reviewer_input, ctx)

    ctx = ReviewerContext(actor_id="inspector", prompt_version="v1-2026-05-22")
    await review_decision(session, _InspectorReviewer(), dossier.id, ctx)

    assert len(received_inputs) == 1
    snapshot = received_inputs[0]["available_info_snapshot"]
    # Outcome leaks must NOT have reached the reviewer
    assert "realized_pnl" not in snapshot
    assert "filled_price" not in snapshot
    assert "outcome" not in snapshot
    # Real info is preserved
    assert "event_payload" in snapshot


# ---------- _build_subprocess_env: auth priority paths ----------


def test_build_env_path1_oauth_token_strips_api_key(monkeypatch):
    """Path 1: CLAUDE_CODE_OAUTH_TOKEN set → forwarded; ANTHROPIC_API_KEY stripped.

    Critical invariant: ANTHROPIC_API_KEY MUST be removed when OAuth token
    is present. Even a non-empty API key would out-precede the OAuth token
    in claude's auth chain and break the subprocess. An empty API key
    (the poison case from the parent CC session) would 401 the call.
    """
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-test-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # the parent CC poison case
    env = _build_subprocess_env()
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-test-token"
    assert "ANTHROPIC_API_KEY" not in env, (
        "ANTHROPIC_API_KEY must be absent when OAuth token is present"
    )


def test_build_env_path1_oauth_overrides_real_api_key(monkeypatch):
    """OAuth token wins even over a non-empty API key — caller has opted into
    subscription billing by setting CLAUDE_CODE_OAUTH_TOKEN."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-realkey")
    env = _build_subprocess_env()
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-token"
    assert "ANTHROPIC_API_KEY" not in env


def test_build_env_path2_api_key_only(monkeypatch):
    """Path 2: API customer, no OAuth token. API key forwarded unchanged."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-realkey")
    env = _build_subprocess_env()
    assert env["ANTHROPIC_API_KEY"] == "sk-ant-api03-realkey"
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in env


def test_build_env_path3_fallthrough_strips_empty_api_key(monkeypatch):
    """Path 3: nothing usable. Strip the empty API-key poison.

    Subprocess will fall through to OAuth keychain, which is known to
    fail under nested CC. But we don't actively block it — caller may
    be running from a fresh terminal where keychain works fine.
    """
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # empty / poisoned
    env = _build_subprocess_env()
    assert "ANTHROPIC_API_KEY" not in env
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in env


def test_build_env_path3_whitespace_api_key_also_stripped(monkeypatch):
    """Whitespace-only API key counts as poisoned, same as empty."""
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    env = _build_subprocess_env()
    assert "ANTHROPIC_API_KEY" not in env


def test_build_env_path3_whitespace_oauth_token_falls_through(monkeypatch):
    """Whitespace-only OAuth token counts as absent."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "   ")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-realkey")
    env = _build_subprocess_env()
    # Falls through to Path 2: API key wins, no OAuth token forwarded
    assert env["ANTHROPIC_API_KEY"] == "sk-ant-api03-realkey"
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in env or not env["CLAUDE_CODE_OAUTH_TOKEN"].strip()
