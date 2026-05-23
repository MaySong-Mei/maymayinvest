# Handoff — for the next Claude

This file is the cold-start checklist when context resets. Read this first; it tells you exactly what to load and in what order. Self-contained.

**Date of last handoff**: 2026-05-23
**Master HEAD at handoff**: `e540c90`
**Commit count since framing reset**: ~35

---

## Read this in order

If your context is fresh, read in this exact order. Each layer assumes you've internalized the prior one.

### Layer 0: Identity (5 min)

1. `v1/docs/PHILOSOPHY.md` — entire doc. **Most important file in the project.**
2. `v1/docs/V1_SCOPE.md` — Stage 0/1/2 plan + 9-item DoD checklist
3. `README.md` — minimal

You ARE the operator. The project is a **self-evolving CC-as-operator trading research system**. Process-based supervision (right bet, not right gain). v1 scope = US equity event-driven right-side. v1 is you-present (not 7x24).

### Layer 1: Architecture (5 min)

1. `v1/docs/ARCHITECTURE.md` — v0 platform skeleton + v1 CC-centric harness
2. `git log --oneline -35` — recent commits to ground yourself in cadence

### Layer 2: Active commitments (10 min)

Open and skim:

1. `v1/docs/proposals/amendments/2026-05-23-amend-bin3-rule-defer-aggregator.md` — current commitment: K=10 corpus entries before aggregator design. **Currently at K=1 valid + 2 contaminated (don't count).**
2. `v1/docs/evals/analyzer-determinism-results-2026-05-23.md` — the bin-3 finding that triggered the amendment
3. `v1/docs/evals/analyzer-determinism-corpus/README.md` — corpus discipline rules; **fixture diversity required; one event = one markdown, closed**
4. `v1/docs/evals/analyzer-determinism-corpus/2026-05-23-defensetech-corp-awarded-850-million-mul.md` — K=1 (valid) entry. Operator picked Trial 2 (notify).
5. `v1/docs/proposals/2026-05-23-add-case6-decision-ambiguous.md` — withdrawn (reviewer pushed back); historical record

### Layer 3: Setup (immediately, before any commit)

```bash
cd v1/backend && make install-hooks
```

Installs `.git/hooks/commit-msg`. **Without this hook installed, you can violate the append-only mandate without realizing it.** The hook is the mechanical enforcement layer.

Also export this (if not already in env):

```bash
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."  # value in user's persistent env
```

This is required for any `claude -p` subprocess (the analyzer + reviewer). Without it, subprocess gets 401.

### Layer 4: Tools you'll use repeatedly

- `v1/backend/scripts/capture_event_to_corpus.py` — capture next corpus entry (K=2..K=10)
- `v1/backend/scripts/eval_reviewer.py` — run reviewer over hand-crafted fixtures
- `v1/backend/scripts/eval_analyzer_determinism.py` — N=5 trials over same event
- `v1/backend/scripts/review_first_real_dossier.py` — pattern for "analyzer + reviewer on one event"
- `v1/backend/scripts/selftest_e2e.py` — full pipeline smoke test

---

## The hard-won invariants you must honor

These are not negotiable. Each came from a real failure mode that bit the project.

### Invariant 1: Right bet, not right gain

Evaluate decisions on **process quality at decision time**, not on outcome. P&L is a long-run consistency check, not the optimization signal. Reviewer must be outcome-blind (architecturally enforced by `build_reviewer_input` stripping outcome-leak fields).

### Invariant 2: Pre-registered rules are binding once outcome arrives

If you locked a rule before observing data, you cannot change its disposition after observing data without going through the **Pre-reg amendment protocol** (PHILOSOPHY.md 8 clauses). The original judgment stands as historical record (clause 6).

### Invariant 3: Append-only operator invariant (most recent, most important)

`v1/docs/PHILOSOPHY.md` "Append-only operator invariant" section. **6 rules + bundling + carve-out + enforcement + bootstrap**. Internalize this fully. The git hook enforces it.

**Most likely failure mode you will hit**: classifying a governance act as "data hygiene" or "small fix" to bypass review. **You cannot self-classify out of the mandate.** The hook checks; if it triggers, dispatch a reviewer or file a `Mentioned-Governance-Keyword: <kw>; reason: <>=20 chars>` declaration.

### Invariant 4: Subagent dispatch is the project's primary muscle

Two uses:
- **Reviewer**: judge a decision or audit a commit (clean-context, may push back)
- **Prober**: empirically test a hypothesis (e.g. "does `claude -p` subprocess inherit parent OAuth?")

When stuck, dispatch a subagent. **Reviewer of reviewer is acceptable** (and has happened multiple times). The user has explicitly invited operator AND reviewers to challenge their own framing.

### Invariant 5: Bundling is the failure mode the mandate exists to prevent

Do NOT mix free-append with review-required actions in one commit. Each kind of action ships in its own commit. The pre-commit hook does not always catch bundling on its own; you must self-discipline.

### Invariant 6: Operator does not silently rephrase to evade hook

If hook triggers on a keyword that you used descriptively (not performatively): **do not rephrase to avoid the keyword**. That is structurally identical to the dd86446 spec-game. Either:
- Wrap the keyword in backticks / quotes / blockquote (C.2 escape), OR
- Add the `Mentioned-Governance-Keyword:` declaration trailer, OR
- Dispatch a reviewer and add `Reviewer-Id:`

---

## What's done (Stage 0 DoD)

| # | Item | Status |
|---|---|---|
| 1 | EDGAR + RSS poller | ❌ |
| 2 | CC-driven analyzer → dossier | ✅ |
| 3 | Technical confirmation gate | ✅ |
| 4 | 3-mode routing (notify/dry_run/auto) | 🟡 (dry_run+promote e2e PASS; notify+auto need selftests) |
| 5 | Reviewer outcome-blind | ✅ |
| 6 | Audit + dossier capture | ✅ |
| 7 | Real risk gate (UI-tunable) | ❌ (stub) |
| 8 | Dashboard signals/pending/promote | ❌ |
| 9 | Skill registry | ❌ |

**3/9 fully done, 1/9 partial, 5/9 open.**

---

## What's running, what's not

### Empirically validated

- ClaudeCodeAnalyzer + ClaudeCodeReviewer subprocess paths (require `CLAUDE_CODE_OAUTH_TOKEN` env var, set via `claude setup-token` in external terminal)
- Reviewer prompt v1-2026-05-22: 5/5 on hand-crafted fixtures, single real dossier judged right_bet at 0.85
- Analyzer prompt v1-2026-05-23: works, but NON-DETERMINISTIC on decision-level output (bin-3 finding)
- Pre-commit hook (commit-msg) enforces append-only mandate, including empty-commit-bypass-closed and substring-overlap-closed
- 89/89 unit tests pass, 4/4 import-linter contracts kept

### Known unfinished

- Real analyzer behavior on N>1 events: unknown (K=1 of 10 corpus)
- Reviewer behavior on more diverse real dossiers: untested
- Operator conservative bias (2 consecutive notify picks): flagged for K=5 review
- Risk gate is a stub
- No EDGAR poller; events are hand-curated fixtures in `tests/fixtures/`

---

## Known residual risks documented

These are NOT closed; bounded by other mechanisms:

1. **Synonym substitution in commit messages** (e.g. "nullify" instead of "void"). Not in keyword list. Mitigation: rule-6 expansion when noticed.
2. **Fake-quote bypass** (operator wraps performative governance text in backticks). Mitigation: post-hoc reviewer audit.
3. **Blanket declaration attack** (operator declares all keywords preemptively). Mitigation: cadence limit = 3 declarations.
4. **30-commit window** for cadence counter. Mitigation: fail-toward-review.
5. **Hand-crafted decision-ambiguity may be unreachable** (case-6 withdrawal finding). Mitigation: wait for real dossier that the operator/reviewer naturally labels ambiguous.
6. **Operator pick bias toward notify** (2/2 so far). Mitigation: K=5 review.

---

## Recommended next move

When you start work, the **first action** should be `make install-hooks` if hook is not present locally.

Then by priority:

**Most likely correct next step**: continue corpus to K=2.
- Use `tests/fixtures/edgar_8k_routine_officer_departure_2024.json` (class 3 non-actionable)
- Run `python scripts/capture_event_to_corpus.py --event tests/fixtures/edgar_8k_routine_officer_departure_2024.json --price MIDC=45.00`
- Read trial outputs only AFTER capture; pick BEFORE looking at any next-loop information
- Commit with K=2 in message (no governance keywords, no `--allow-empty` shortcuts)

**Other defensible candidates**: DoD #4 notify/auto selftests; DoD #1 EDGAR poller (large); DoD #8 dashboard signals page

**NOT recommended**: more governance/framework work without a budget reason. The last 6 commits were heavy on hook iteration. Operator self-imposed budget: governance commits must be followed by DoD/data progress within ~48h.

---

## Subagent dispatch patterns that worked

When you dispatch, use these patterns (refined over ~15 successful dispatches):

### Reviewer pattern
```
You are a Dialogue Reviewer for the maymayinvest project.

Read first: PHILOSOPHY.md "Append-only operator invariant" section.
Then read: <specific files relevant to the decision>.

Context: <one-paragraph what just happened>
The decision under review: <operator's proposal verbatim>

Audit specifically: <named questions, not generic>
Output format: <structured PART 1, PART 2, ... + CONFIDENCE>

Be willing to REJECT or REQUEST CHANGES. The user has explicitly
invited reviewer to challenge operator AND user framing.
```

### Prober pattern (epistemic, not evaluative)
```
You are a technical prober. Your job: empirically determine <hypothesis>.

Hypotheses to test: H1: ..., H2: ..., H3: ...

Investigation tools: Bash, WebFetch, file Read.

Constraints: do NOT consume API budget; do NOT modify files.

Output: each hypothesis with YES/NO/PARTIAL + evidence + confidence.
```

---

## The single sentence that captures this project

> *"The operator is a fallible agent helping build a system that constrains itself; the user is an oversight checker on both."*

If a future decision contradicts that sentence, the decision is wrong, not the sentence.

---

## Past key reviewer agent IDs (for cross-reference in commit messages)

- `ab5e8f0e1cd382d43` — case-3 relabel APPROVE
- `a67350f3185d0fae1` — case-6 fixture REJECT
- `a26ded8154a8298b5` — candidate-2 (promote_signal) recommendation
- `ad4ba152aaf8e3353` — candidate-1 (ClaudeCodeAnalyzer) recommendation
- `ab8ab398ade61ba99` — pre-reg required (HARKing prevention)
- `ad2b90c4c8f1f4cd7` — pre-reg plan 4 defects
- `a54c86a35cbad8dbf` — first amendment review APPROVE
- `a6a154bac3af1e4e6` — first mandate-draft REVISE-first
- `a8b18d32d72af4338` — append-vs-reinterpret refinement REVISE
- `ad050467ff8bc9213` — dd86446 post-hoc audit
- `a3441000d2edaf2f4` — empty-commit bypass discovery
- `a372e9abf32c70bf0` — empty-commit fix APPROVE
- `a0513e14879df99e1` — Candidate C design
- `aadf7e1baeeb097bb` — multi-keyword bypass discovery
- `a8af941cce966d72f` — substring overlap bypass discovery
- `a142cc6aa62064d43` — final C-patch APPROVE

Each of these is in git log; you can find the full output by searching commit messages or `--grep` on the agent ID.

---

## One last thing

The user is patient and trusts the process when it produces value. They have multiple times pushed back when the operator was building scaffolding faster than evidence justified. **Listen to that signal.** The mandate, the corpus, the eval framework — they only matter if they produce real CC trading decisions that we can learn from.

K=1 of 10 is the load-bearing fact. Everything else is foundation.

Good luck.
