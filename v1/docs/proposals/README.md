# Proposals

Structured-change documents for goal-level / metric-level / prompt-level / harness-invariant updates. See `../PHILOSOPHY.md` § "Goal evolution as a process-based decision".

## When to write a proposal

Write one before:
- Changing a reviewer prompt version (`v1/backend/app/intel/reviewer/prompt.py`)
- Adding or removing a flag in the reviewer taxonomy
- Adjusting risk gate caps (single-order cap, daily notional cap, max open positions)
- Changing the definition of `right_bet` / `wrong_bet` / `ambiguous`
- Modifying any architectural invariant in PHILOSOPHY.md or ARCHITECTURE.md
- Modifying the `_OUTCOME_LEAK_FIELDS` set in `app/persistence/repositories/decisions.py`
- Promoting a new skill to the registry (see future skill-registry path)
- Anything that would feel like "I'll just tweak this and re-run" — that feeling is the trigger

## When NOT to write a proposal

- Bug fixes (test fails → make it pass)
- Adding a new test
- New module that doesn't change the goal/metric definitions
- Routine refactors that preserve behavior

## File naming

`YYYY-MM-DD-<artifact>-<short-slug>.md`

Examples:
- `2026-06-15-reviewer-prompt-v2-relax-confidence-calibration.md`
- `2026-07-01-risk-gate-raise-daily-notional-from-2k-to-5k.md`

## Template

```markdown
# Proposal: <title>

**Date**: YYYY-MM-DD
**Author**: <operator id, e.g. "claude-instance-1" or "human-direct">
**Artifact**: <which file / config / prompt version is being changed>
**Cool-down expires**: YYYY-MM-DD (14 days after this proposal)

## What changes

<concrete: from X to Y; show the diff in prose>

## Why

<reasoning in current information. cite past commits or proposals if relevant>

## What metric is expected to move and in what direction

<be specific. "right-bet rate goes up" alone is insufficient — say from what to what, on what dataset>

## What would falsify this proposal

<the explicit criterion that, if observed, says "this change was wrong"; commits to a revert path>

## Alternatives considered

<other ways to achieve the same goal that were rejected, with why>

## Confidence

<0.0 - 1.0, with explicit caveat on what you're uncertain about>

## Reviewer judgment

<filled in by goal_change_reviewer subagent or by direct human review; do not pre-fill>

## Approval

<filled in only by human merging the PR; do not pre-fill>
```

## After approval

Once a proposal is merged:
1. The cool-down clock starts. No further changes to the same artifact for 14 days.
2. The code change implementing the proposal goes in a subsequent commit, referencing the proposal file in the commit message.
3. After the cool-down, if the change is to be reverted, that requires a new proposal — no silent rollbacks.
