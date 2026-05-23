# Git hooks for append-only operator invariant

This directory holds the pre-commit hook enforcing the rules in
`v1/docs/PHILOSOPHY.md` "Append-only operator invariant".

## Install

From repo root:

```bash
cp v1/backend/scripts/git-hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
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

`.git/hooks/pre-commit` is local to your clone and not in git. You CAN
remove it. But: the file `v1/backend/scripts/git-hooks/pre-commit` IS
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
