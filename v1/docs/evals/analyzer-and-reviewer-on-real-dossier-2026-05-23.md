# First real dossier — analyzer + reviewer findings

**Date**: 2026-05-23
**Analyzer prompt**: `v1-2026-05-23`
**Reviewer prompt**: `v1-2026-05-22`
**Event**: Apple 2024-05-02 8-K, $110B buyback + Q2 results (hand-curated, source=`manual`)
**Raw output**: `v1/docs/evals/reviewer-on-real-dossier-2026-05-23.json`
**Selftest-e2e raw output**: captured in commit `5ae95c3` message

This is the first time a non-stub DecisionDossier has been produced (commit `5ae95c3`) and the first time a DecisionReview has judged one (this commit). The "hardest unsolved problem" in PHILOSOPHY.md gets its first real-data data point.

The findings are non-trivial in both directions.

## Finding 1: Analyzer is NOT deterministic across runs

The same prompt, the same event, the same snapshot, fed to two separate `claude -p` invocations 10 minutes apart, produced **structurally different dossiers**:

| field | first run (selftest_e2e) | second run (this eval) |
|---|---|---|
| dossier id | 26352c77-... | b31303f9-... |
| mode | `dry_run` | `notify` |
| confidence | 0.6 | 0.6 |
| proposed.intent | AAPL BUY 2 (limit) | **null** |
| no_action_reason | null | "info insufficient to size — defer to next-loop with confirmation criteria" |
| alternatives count | 4 | 5 |
| stance on stale snapshot | "noticed price stale, but sized anyway using stale price" | "info insufficient including price; refuse to encode stale-priced sizing into a dry_run row" |

Confidence numerically identical (0.6) but **decision identity completely different**. One run produced an order intent; the other refused to size at all.

### Interpretation

Two related but distinct observations:

1. **Stochasticity of analyzer output**. LLMs are not deterministic by default. The second run was more conservative and more framework-internally-consistent than the first. Both are defensible; neither is wrong. But the system needs to acknowledge that *the same situation can produce different intents on different runs*.

2. **Quality drift toward better behavior on the second run**. Run 2 caught the "don't size against stale price" implication and acted on it; run 1 noticed the staleness but proceeded with sized output anyway. The second is structurally better reasoning. This is good — but we should not assume run-to-run will trend toward "better" reliably. It might just have been noise.

### Implications

- Single-run analyzer eval is insufficient for any non-trivial conclusion. The "5 fixture × 1 run" reviewer eval was OK because *those fixtures were hand-crafted and deterministic*; analyzer eval over real events needs N≥3 per case to even start distinguishing signal from noise.
- The Goal state machine threshold (attempts < 3 + cost < cap) — originally designed to handle reviewer disagreement — is now ALSO the right shape for handling analyzer non-determinism. Run analyzer 3 times before treating one verdict as load-bearing.
- The system needs to **persist multiple analyses per event** if we want to capture this. Currently the schema allows it (a single event can have N dossiers) but no code path exercises that.

## Finding 2: Reviewer judged second-run dossier as `right_bet` at 0.85, with a structural critique

Reviewer's verdict on the (second-run) dossier: `right_bet`, confidence `0.85`, no flags. Reasoning excerpts:

> "The decision to NOT submit an order intent and instead emit a notify signal is the correct process call under the stated right-side, event-driven framework."

> "The framework requires post-event price confirmation, and the operator has none. Acting on the 8-K body alone would be left-side, pre-confirmation trading — the operator names this explicitly and refuses."

> "Five distinct alternatives are considered, including the symmetric short case and two intermediate actions (small probe, dry_run queue). Each rejection is justified on framework grounds, not on outcome prediction."

> "The rejection of the dry_run queue is particularly well-reasoned: encoding sizing now against stale pre-event price would propagate a stale decision forward; notify defers the decision to a state where better information exists."

This reviewer reasoning is **sharper than the analyzer's reasoning**. The reviewer crystallized the framework-level argument ("we have no post-event price ⇒ pre-confirmation trading violates right-side") more cleanly than the analyzer's own prose did.

### Reviewer's only critique

> "The pre-defined confirmation criteria (gap holds above $220.50, above-average volume, no immediate fade) and invalidation criteria (close back below $220.50) are stated as forward instructions for the next loop, but the operator does not formally hand them off as structured fields — they live in prose."

This is a **schema-level suggestion** the reviewer surfaced unsolicited: `DecisionDossier` should carry structured `confirmation_criteria` and `invalidation_criteria` fields, not bury them in prose. The reviewer is asking for a structural upgrade to make the next-loop-trigger machine-readable.

This is a real signal. The reviewer is more right than the current dossier shape allows it to be. Worth a proposals/ entry.

## Finding 3 (CORRECTED): Reviewer wasn't given a chance to fail on the stale-snapshot inconsistency

**Initial framing (incorrect, retained for honesty)**: "Reviewer did not flag the stale-snapshot inconsistency that the previous run's analyzer self-caught."

**Corrected framing (per dialogue reviewer `ab8ab398ade61ba99`)**: The reviewer was judging the **second run's** dossier, where the analyzer *did* refuse to size against stale data (mode=`notify`, no intent). The reviewer was not given an analyzer that ignored the staleness. So the reviewer's "failure" to flag a stale-data issue is not a reviewer failure — there was no failure to flag.

The original Finding 3 conflated two separate questions:

- **Question 3a**: When the analyzer DOES output a sized intent against stale data (as run-1 did), does the reviewer catch the inconsistency? **Not tested yet** — that test requires a dossier with a sized intent AND stale data. Run-2 had neither.

- **Question 3b**: Should the reviewer prompt direct internal-consistency checks (event timestamp vs snapshot data temporal coherence)? **Still a worthy question** for a reviewer prompt v2. But it is now a hypothesis to investigate, not a finding from this run.

### What is preserved

The conceptual lesson — that internal-consistency checks are within the reviewer's scope (outcome-blindness applies to future state, not to whether input was self-consistent) — remains valid. The reviewer prompt could profitably be upgraded to explicitly request internal-consistency review. This is a candidate proposal but should not be filed until question 3a is empirically tested at least once.

### The dev-seed confound

The stale-data scenario was not a deliberately constructed eval case. It came from `app/engine/broker_registry.py:_DEV_QUOTES = {"AAPL": Decimal("220.50")}` — a dev-environment seed quote that pre-dates the analyzer work. It leaked into the first real run because no one connected the dev seed to the May 2024 event timestamp. The right move is to **clean the dev seed** (separate small commit) rather than treat its accidental presence as a meaningful test case.

The audit trail of the stale-data behavior is preserved in:
- commit `5ae95c3` message (the first run's self-flag)
- this document (the original mis-framing of Finding 3)
- the raw JSON snapshots of both runs

so cleaning the seed does not erase the finding's data.

## What this tells us about v1's "hardest unsolved problem"

Restate: PHILOSOPHY.md identifies the load-bearing assumption as
> "the reviewer subagent must be able to judge right-bet reliably from information-only basis, without ground truth outcomes."

After one real data point, the question splits:

| sub-question | answer (preliminary, N=1) |
|---|---|
| Can reviewer judge process quality on real dossiers? | Yes — `right_bet` at 0.85 with substantive reasoning, sharper than analyzer's own prose. |
| Does reviewer catch every relevant defect? | No — missed the stale-snapshot inconsistency (Finding 3). |
| Does reviewer offer structural feedback beyond verdict? | Yes — surfaced a `confirmation_criteria` schema suggestion unsolicited (the "only minor critique"). |
| Is the assumption "load-bearing-true"? | **Cautiously yes** — but the gaps (Finding 3) mean the supervision layer needs iteration, not adoption-as-is. |

The honest read: the system **works**. The reviewer is providing real signal. It's not perfect, and the imperfections are diagnosable — which is exactly what the framing said would happen ("v1 is partly an experiment to find out").

## What does NOT happen as a result of this finding

- Reviewer prompt is NOT modified in this commit. Any change goes through proposals/ + cool-down.
- DecisionDossier schema is NOT modified to add confirmation_criteria. That's a proposal too.
- Analyzer prompt is NOT modified. The non-determinism finding suggests we should run N=3 attempts per event going forward, not change the prompt.
- We do NOT generalize from N=1 dossier to "the system works in production". One data point is one data point.

## Next steps — operator's plan (after dialogue reviewer `ab8ab398ade61ba99`)

The operator initially proposed A → B → C → D in that order, with A as the lean. Dialogue reviewer modified the sequence and added two constraints. Operator accepted in full:

1. **E (NEW, before A): fix `_DEV_QUOTES`** in `app/engine/broker_registry.py`. The stale-AAPL-$220.50 seed is dev infra leaking into a production-shaped test. Replace with a value that won't trigger the same accidental Finding 3 (or remove the seed entirely and require explicit setup in tests/dev). Small commit, isolated.

2. **A (modified): test analyzer determinism with PRE-REGISTERED analysis plan.**
   Before running N=5 trials, write down (in a separate `v1/docs/evals/analyzer-determinism-eval-plan-2026-05-23.md` file):
   - What `(mode, intent presence, confidence)` distribution counts as "deterministic enough to ship"
   - What distribution counts as "needs prompt work"
   - What distribution counts as "needs N>1 per event in the production loop"
   The plan goes to git BEFORE the runs. Otherwise the trials risk HARKing — hypothesizing after results known, on a tiny sample.

3. **(defer) B (reviewer prompt v2 with internal-consistency checks)**. Worth doing, but blocks reviewer-side work for 14 days during cool-down. Wait for at least the N=5 data from A before committing the reviewer-side gate.

4. **(defer) C (structured `confirmation_criteria` / `invalidation_criteria` schema)**. Same reason — it's a sizable change to PHILOSOPHY-adjacent contracts. Wait for more evidence about whether this is the right schema upgrade, or whether dossier prose is actually serviceable.

5. **D (EDGAR poller)** is correctly LAST in this sequence. Broadening to multiple events without first establishing the per-event noise floor (A) means sample-size-2 noise reads as signal.

The dialogue reviewer also surfaced a meta-point worth recording: the operator is currently in a productive groove. The right step-back is not "stop" but "pre-register analysis plans before running new evals." That is the cheapest insurance against pattern-completion drift.

### Operator's pre-registration commitment

For the A step, the analysis plan file must be a separate commit landed before any of the N=5 trials are run. The trials' raw output and analysis go in a subsequent commit. Splitting the artifact prevents "I see the results now, let me adjust what I would have predicted" — a form of HARKing that the proposal flow normally prevents but isn't applicable to non-proposal investigations like this.
