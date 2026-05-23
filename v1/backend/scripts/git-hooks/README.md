# Git hooks for append-only operator invariant

This directory holds the commit-msg hook enforcing the rules in
`v1/docs/PHILOSOPHY.md` "Append-only operator invariant".

Note: this is a `commit-msg` hook (not pre-commit) because the
mandate requires checking commit message trailers. The pre-commit
hook runs BEFORE the message is written, so it cannot see the
trailer. commit-msg runs AFTER the message is written but BEFORE
the commit is finalized, which is the correct phase.

## Install

From repo root:

```bash
cp v1/backend/scripts/git-hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Or use the Makefile target:

```bash
cd v1/backend && make install-hooks
```

## What the hook does

Scans `git diff --cached`. If the diff:
- Modifies (not pure-add) a file in the review-required surface, OR
- The commit message contains a keyword suggesting re-interpret/binding
  action (lock pre-reg, void k=, recount, contamination, amend, etc.)

...then the commit requires one of:
- `Reviewer-Id: <agent-id>:<diff-hash>` trailer (after fresh-brain review)
- `Non-Semantic: <reason>` trailer (for typo / link / whitespace fixes)

Otherwise: rejected with explanation.

## Why this hook exists

`dd86446` (2026-05-23) demonstrated that self-imposed budgets are
insufficient — the operator can sincerely classify a commit out of any
rule it gets to interpret. This hook removes that interpretation space.

## Removing the hook

`.git/hooks/commit-msg` is local to your clone and not in git. You CAN
remove it. But: the file `v1/backend/scripts/git-hooks/commit-msg` IS
versioned and is itself in the review-required surface — so removing
it from the repo (vs from your local hooks dir) requires a reviewed
commit. Local removal is allowed for emergency use but should be
documented and reverted ASAP.

## Edge cases the hook does NOT catch

- Operator commits using `--no-verify` to bypass the hook. There is
  no mechanism to prevent this; it relies on git log auditing.
- Operator's local hook is out of date. Re-install after pulling.
- Server-side check is not currently implemented. Future work:
  CI pipeline that re-runs the hook on each pushed commit.
