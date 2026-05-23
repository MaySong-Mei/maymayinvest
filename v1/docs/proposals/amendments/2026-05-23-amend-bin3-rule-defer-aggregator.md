# Amendment: Defer aggregator code; build determinism observation corpus

**Type**: Pre-reg amendment (per PHILOSOPHY.md "Pre-reg amendment protocol")
**Date**: 2026-05-23
**Author**: claude-code-operator
**Artifact target**: bin-3 disposition in `v1/docs/evals/analyzer-determinism-eval-plan-2026-05-23.md` (commit `90e4db1`)
**Cool-down expires**: 2026-06-06 (14 days)
**Status**: Filed; awaiting fresh-brain reviewer per amendment protocol clause 5, then human approval per clause 8.

---

## Amendment manifest (per protocol clause 4)

### Field 1: Raw evidence

- Pre-reg plan: `v1/docs/evals/analyzer-determinism-eval-plan-2026-05-23.md` (locked at commit `90e4db1`)
- Outcome writeup: `v1/docs/evals/analyzer-determinism-results-2026-05-23.md` (commit `6e3cb3b`)
- Raw trial JSON: `v1/docs/evals/analyzer-determinism-results-2026-05-23.json` (5 trials, all fields)
- First real dossier writeup (Finding chain that produced bin-3 question): `v1/docs/evals/analyzer-and-reviewer-on-real-dossier-2026-05-23.md` (commit `b53075b`)
- Two dialogue reviewer outputs (full text in commit messages of `bc574f0`-era prep and below):
  - Reviewer `a10c75b4e38620544` (design-space mapping; recommended D+E "cheapest first proposal")
  - Reviewer `ad49a25df845c280f` (steel-man against D+E; recommended defer + observation corpus)

### Field 2: Original rule (verbatim, from `90e4db1`)

> "**Bin 3 → "Stochastic on decision"**
>
> Bin 3 → DO NOT move to D yet. The system needs a multi-analysis-per-event aggregation strategy. Operator files a proposal for that, which is itself an A-tier finding. B and C are deferred until aggregation strategy is settled."

### Field 3: Observed outcome (verbatim, from `6e3cb3b`)

5 trials over same event + same prompt + same snapshot:

| trial | mode | intent_is_null | confidence | qty |
|---|---|---|---|---|
| 1 | dry_run | false | 0.62 | 1 |
| 2 | notify | true | 0.62 | — |
| 3 | dry_run | false | 0.62 | 2 |
| 4 | dry_run | false | 0.60 | 1 |
| 5 | notify | true | 0.65 | — |

2 distinct `(mode, intent_is_null)` patterns. 0 subprocess errors. 0 parse errors. Mechanical bin assignment by locked rules → **Bin 3**.

### Field 4: Original disposition

The operator must "file a proposal for a multi-analysis-per-event aggregation strategy." B and C remain deferred. D is blocked until aggregation is settled.

### Field 5: Proposed revision

Revise bin-3 disposition to: **"File an amendment proposal that EITHER specifies the aggregator design OR specifies a corpus-observation-first strategy as an intermediate step before aggregator design. If the corpus-observation-first path is chosen, K=10 corpus entries (each event analyzed N=3 times with operator manual pick recorded) must be accumulated before any aggregator code is written. The B-and-C deferral stays in effect during corpus accumulation."**

Functionally: instead of going straight from bin-3 to aggregator design, the protocol allows a corpus-evidence-gathering step in between, with strict bounds (K=10 events).

### Field 6: Why this is not outcome-regret (LOAD-BEARING)

The amendment is grounded in **two pieces of information the operator did NOT have when authoring the pre-reg plan**:

1. **A higher-order invariant became visible only after seeing the design space.** When the pre-reg plan was written, the implicit assumption was "aggregator design is a well-defined task." Reviewer `ad49a25df845c280f` later pointed out that the most-obvious aggregator forms (the "synthesized notify-only dossier" D+E sketch) violate the Decision-table authorship invariant — Decision rows must record what an actor actually decided, and a fabricated dossier authored by an aggregator is not that. This invariant existed in `app/persistence/models.py:165-194` BEFORE the pre-reg plan was written, but its conflict with aggregator design was not anticipated. The pre-reg plan didn't say "build aggregator IF design doesn't violate invariants"; it said "build aggregator." Discovering the invariant-conflict is **new information about the constraint space**, not new information about the outcome.

2. **The pre-reg plan did not enumerate "evidence-base size required" as a parameter.** It assumed N=5 trials on ONE event would be sufficient grounding for aggregator design. After running, the operator (and reviewer `ad49a25df845c280f`) noticed: N=5 trials on N=1 event can only show *whether disagreement happens* — it cannot tell whether disagreement is event-class-specific (borderline 8-Ks split this way) or systematic (the analyzer splits on everything). These two cases require different aggregators. Designing aggregator on N=1 event is premature optimization. This is **new information about the dependency structure of aggregator design**, not new information about whether to dislike the outcome.

**Concrete test for outcome-regret**: would the operator file this amendment if bin-3 had produced "5/5 agree on dry_run + BUY 2 limit"? **No** — that would have been bin 1 or 2, and the bin-3 disposition would not have fired. The amendment is specifically about *what to do when bin-3 fires in this evidence regime*, not about avoiding the disposition because the outcome was inconvenient. The outcome itself (decision-level instability) is taken at face value, not reinterpreted.

**Counter-test for spec-gaming**: if the protocol allows this amendment, what's to stop *every* bin-3 firing from being amended into "do something cheaper instead"? The answer is: future bin-3 firings, given the precedent established here, would need to surface either (a) a NEW higher-order invariant the aggregator design would violate, or (b) NEW evidence about the dependency structure of aggregator design. Neither is automatically available; they require concrete grounding. If a future operator tries to amend bin-3 with "I just want to defer again," there is no new information and the amendment should be rejected.

---

## Context

The pre-registered analyzer determinism experiment (plan `analyzer-determinism-eval-plan-2026-05-23.md`, results `analyzer-determinism-results-2026-05-23.md`, commit `6e3cb3b`) landed in **bin 3 — "Stochastic on decision"**. The locked decision rule for bin 3 says:

> "Bin 3 → DO NOT move to D yet. The system needs a multi-analysis-per-event aggregation strategy. Operator files a proposal for that..."

This proposal is the required filing. **But the proposal content is not "build aggregator now."** It is "build the evidence base that aggregator design requires."

## What this proposal is and is not

**Is**: a process commitment to capture the next K real events (K=10 default) through a manual N=3 analyzer-trial loop, record the patterns and the operator's manual pick, and use that corpus as the evidence base for the eventual aggregator design.

**Is not**: a deferral disguised as a proposal. The bin-3 rule is honored: a proposal is filed; aggregation is the topic; the proposed mechanism is documented; the falsification path is concrete.

## What changes

1. New directory: `v1/docs/evals/analyzer-determinism-corpus/` (empty at this commit; populated as real events arrive).
2. New script: `v1/backend/scripts/capture_event_to_corpus.py`. Given an event payload (JSON path or stdin), runs the analyzer N=3 times (with a snapshot provider supplied via flags), persists all 3 dossiers to an in-memory sqlite (NOT to a persistent DB — this is research data, not production state), and emits a single markdown file to the corpus directory containing:
   - the event's external_id, kind, headline
   - the 3 dossiers' `(mode, intent_is_null, confidence, qty if intent, side if intent)` tuples
   - the first 200 chars of each reasoning_chain
   - a blank "operator's manual pick" section the operator fills in by hand BEFORE looking at any next-loop information
3. The operator commits each corpus entry as its own commit so the timestamp of the operator's decision is traceable.

## Why this instead of building an aggregator

Three reasons, in increasing order of weight:

1. **N=1 disagreement event is not enough evidence to design aggregation.** The bin-3 finding was over a single 8-K. We don't yet know if the disagreement is event-class-specific (only borderline 8-Ks split this way), regime-specific (the analyzer always splits on post-close events), or systematic (the analyzer splits on everything roughly equally). Each of these implies a different right aggregation strategy. Designing one now would be premature optimization on a sample of one.

2. **The "synthesized notify-only dossier" pattern that the design-space-mapping reviewer suggested as the cheapest aggregator violates an architectural invariant.** Reviewer `ad49a25df845c280f` specifically flagged: a Decision row whose `reasoning_chain` is operator-authored prose (not analyzer-authored) breaks the implicit contract that Decision rows are append-only records of what an actor actually decided. The aggregator would either need to lie about authorship (set `actor_id="aggregator-v1"` and pretend it's an actor — adds a new architectural concept under the guise of "smallest change") or break the contract directly. Neither is a small change. Both should be considered explicitly via their own proposal, not folded into "aggregation."

3. **The proposal-flow itself is showing signs of becoming the work.** Seven of the eight commits since framing reset (`5df5a9a` onward) are governance/eval machinery, not v1 Stage 0 definition-of-done items. The bin-3 rule was a faithful application of the locked plan, but the plan was written before we knew that N=1 event would be the evidence base. The honest move is to acknowledge the gap and accumulate evidence before adding more governance scaffolding.

## What corpus capture looks like in practice

When a real event arrives (synthetic or real, EDGAR or hand-curated for now):

1. Operator places event JSON in `tests/fixtures/` or supplies it inline.
2. Operator runs `python scripts/capture_event_to_corpus.py --event tests/fixtures/<file>.json --aapl-price 220.50` (or relevant snapshot args). The script:
   - Runs ClaudeCodeAnalyzer 3 times serially.
   - Records each dossier's outcome features (the same set used in the determinism plan).
   - Emits a markdown stub to `v1/docs/evals/analyzer-determinism-corpus/<YYYY-MM-DD>-<event-slug>.md`.
3. Operator opens the markdown, reads the 3 reasoning chains, and writes their manual pick + 1-3 sentences of why in the dedicated "operator pick" section.
4. Operator commits the markdown.

Per-event cost: ~$0.20 subscription draw + ~3 minutes of operator reading + 1 commit.

## Metric expected to move and direction

After K = 10 corpus entries (default K), the operator examines aggregate patterns:

- **What % of events showed decision-level disagreement (mode or intent_is_null varied across the 3 trials)?**
- **For disagreeing events, did the operator's manual picks cluster systematically (e.g. operator usually picks the most conservative)?**
- **Were there parse / subprocess errors?**

If decision-disagreement rate is **< 30%**: aggregation is a small problem; a simple "first-of-3" or vote rule will work; design will be straightforward.

If decision-disagreement rate is **30-70%**: aggregation is the right project; reviewer-mediated or human-in-the-loop strategies become preferred; design proposal follows the corpus evidence.

If decision-disagreement rate is **> 70%**: aggregation is the WRONG framing. The analyzer is too noisy to ship; the proposal would shift to prompt v2 or model-temperature investigation. This is reviewer 8's falsifier, materialized.

## Falsification

This proposal is wrong (and should be revised or replaced) if:

1. **K=10 events take longer than 6 weeks to accumulate** (real or hand-curated): the corpus loop is too slow to be useful and we need to either lower K or seed with synthetic events.
2. **Operator manual picks become rote** (>80% one pattern) before K=10 — that would indicate the operator's pick is not adding information beyond the analyzer's modal output and we should just use the mode.
3. **A real opportunity to act on a real event is lost while corpus building is in progress** — the corpus serves the system, not the other way around; if the system needs to act and we don't have aggregation, the deferral was too long.

## Alternatives considered

1. **Build D+E (reviewer 8's sketch) as proposed.** Rejected per reviewer 9's authorship-invariant objection AND the "design on N=1" concern. The risk of shipping the wrong aggregation is higher than the cost of waiting.

2. **Build the smallest possible "majority vote on first-tier features" aggregator with no synthesized dossier — instead surface a `decision_group_id` and let the dashboard show multiple dossiers.** This is a real alternative. It is smaller than D+E and respects authorship. **Rejected for now** because it still commits to "vote is the right aggregation" before we have the corpus. After K=10, this might become the proposed strategy, but only on evidence.

3. **Do nothing at all — no proposal, no corpus, just wait.** Rejected: violates the locked bin-3 decision rule. The bin-3 rule was honest pre-registration; reneging on it post-result is exactly the HARKing the framework is meant to prevent.

4. **Lower N from 3 to 2 in the corpus capture.** Cheaper per event, but the N=2 we already have (commits `5ae95c3` and `b53075b`) gave 2 distinct patterns — N=2 systematically under-detects 3-pattern situations. N=3 is the minimum that can show 2-2 splits AND 3-distinct. Keep N=3.

5. **Apply this proposal to synthetic events only, not real ones.** Considered. Rejected because synthetic events are the operator's labels and inherit operator bias (see case-6 withdrawn proposal). Real events are the evidence we actually need.

## Reviewer judgment

### Design-space dialogue reviewers (pre-amendment, informational)

- Reviewer `a10c75b4e38620544`: mapped aggregator design space; recommended "D+E" sketch as cheapest first proposal. Confidence 0.74.
- Reviewer `ad49a25df845c280f`: steel-manned AGAINST D+E sketch. Recommended defer + corpus. Confidence 0.78.

These two consultations shaped the amendment content but did NOT formally review the amendment itself.

### Pre-reg amendment reviewer (per protocol clause 5)

**Reviewer ID**: `a54c86a35cbad8dbf` (first-ever Pre-Reg Amendment Reviewer invocation)
**Decision**: APPROVE (with caveat for human gate)
**Reviewer confidence**: 0.72

**Field-by-field audit results**:
- Field 1 (raw evidence): PASS — spot-checked raw JSON against markdown table; consistent.
- Field 2 (original rule): PASS WITH MINOR CAVEAT — the bin-3 disposition quote matches verbatim; the prepended "Stochastic on decision" header is from a different line (the bin name table) but no smuggling.
- Field 3 (observed outcome): PASS — table matches raw JSON exactly; mechanical bin-3 assignment correct.
- Field 4 (original disposition): PASS — restatement faithful.
- Field 5 (proposed revision): CONCRETE — K=10, N=3, falsifiers, time-box all specified.
- Field 6 (why-not-outcome-regret): **PARTIAL PASS**.
    - Argument (a) — Decision-table authorship invariant — is **partially convincing**. The Decision schema has `actor_id`, `actor_type`, `reasoning_chain` + "append-only at application layer" comments, but there is NO explicit schema-level "no fabricated rows" constraint. The "authorship invariant" is **interpretive**, not literal. The amendment overstates it as a hard pre-existing constraint.
    - Argument (b) — N=1 event is structurally insufficient for aggregator design regardless of bin-3 direction — is **fully convincing**. This argument would survive the counter-test (see below) and grounds the amendment independently of (a).
    - Net: amendment is not outcome-regret in technical clothing, but its strongest leg is (b), not (a).

**Counter-test applied (per protocol clarification 1)**:
> "Would the operator have filed THIS amendment if bin-3 had fired with a different disagreement shape (e.g. 3 notify + 2 dry_run instead of 3 dry_run + 2 notify)?"

Both arguments (a) and (b) are outcome-shape-invariant within bin-3. The amendment depends on bin-3 firing (the trigger) but NOT on which way the disagreement leaned. **Passes the counter-test.**

**Reproduction requests**: None. Evidence packet was sufficient.

**Caveat for human gate**: The amendment is APPROVED but the human should explicitly judge whether the Decision-table "authorship invariant" claim (field 6 argument (a)) counts as a "higher-order invariant" per protocol clause 3, or whether only argument (b) — the N=1 evidence-base limit — is doing the work. If the latter, the amendment still stands but on narrower grounds; future amendments citing similar "interpretive invariant violations" should face higher scrutiny.

### Operator's read on the reviewer's caveat

I agree with the reviewer's caveat. Specifically:

- I overstated argument (a). The Decision-table authorship "invariant" is more of a **conceptual reading** than a schema-enforced rule. Future amendments should not cite interpretive invariants as if they were enforced.
- Argument (b) is sufficient on its own. The amendment's claim is: "N=1 event is too thin to design aggregator." This is a real, structurally outcome-shape-invariant epistemic limit that the pre-reg plan did not anticipate.
- This is itself a **lesson from the protocol's first run**: amendments should distinguish clearly between schema-enforced invariants (hard) and conceptual invariants (interpretive). Future amendment template should ask the operator to grade their own invariant claims.

## Risks

1. **Corpus accumulation may stall.** The system needs real events to feed it, but the EDGAR poller is not built. v1 Stage 0 is "you-present" so synthetic events are valid, but the operator must ensure they're curated honestly (no cherry-picking the events that produce interesting outputs).

2. **The "operator's manual pick" data is operator-bias-prone.** This is acknowledged in the falsification path (rote picks). Mitigation: future review of the corpus by a fresh-context subagent ("does the operator's pick seem to follow the analyzer's majority?"), separate from the corpus building.

3. **Deferring aggregator is not a moratorium on aggregation thinking.** If during corpus building a clear pattern emerges, the operator MAY file a follow-up proposal early. The 14-day cool-down attaches to the "aggregator design" topic, not to corpus capture — but jumping from corpus to aggregator before K=10 needs explicit justification.

4. **The proposal flow's cool-down was designed for code/prompt changes. This proposal is a process commitment.** If the operator wants to revise the corpus protocol (change K, change capture script behavior) inside the cool-down window, that's a small revision that should not trigger a new full proposal. But it should be explicitly noted in this proposal's update log.

## Approval

(To be filled by user when merging or rejecting.)
