# Proposal: Defer aggregator code; build determinism observation corpus

**Date**: 2026-05-23
**Author**: claude-code-operator (proposed); two dialogue reviewers consulted (`a10c75b4e38620544` mapped design space, `ad49a25df845c280f` steel-manned against the design space's "cheapest" sketch)
**Artifact**: NEW process artifact — `v1/docs/evals/analyzer-determinism-corpus/` directory + `scripts/capture_event_to_corpus.py` runner. NO changes to persistence schema, NO new code in app/intel/, NO new capability.
**Cool-down expires**: 2026-06-06 (14 days; binding only on "aggregator design" — the actual artifact this proposal modifies is the observation process, which is not under cool-down)

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

This is a process artifact more than a code artifact. The two dialogue reviewers consulted on the design space are recorded above. Their findings shaped this proposal but neither was given a vote on "should this be filed."

The operator deliberately did NOT invoke a third dialogue reviewer to review this proposal. Reason: the marginal value of a third opinion is low when the two existing reviewers already converged on (a) "don't build the synthesized-dossier aggregator" and (b) "evidence is too thin to design now." A third reviewer would either confirm (no new information) or disagree (and we'd be in a 2-vs-1 with the operator already aligned with the 2).

If the human reviewer (you) disagrees with this assessment and wants a third dialogue reviewer involved before merging, the operator will invoke one.

## Risks

1. **Corpus accumulation may stall.** The system needs real events to feed it, but the EDGAR poller is not built. v1 Stage 0 is "you-present" so synthetic events are valid, but the operator must ensure they're curated honestly (no cherry-picking the events that produce interesting outputs).

2. **The "operator's manual pick" data is operator-bias-prone.** This is acknowledged in the falsification path (rote picks). Mitigation: future review of the corpus by a fresh-context subagent ("does the operator's pick seem to follow the analyzer's majority?"), separate from the corpus building.

3. **Deferring aggregator is not a moratorium on aggregation thinking.** If during corpus building a clear pattern emerges, the operator MAY file a follow-up proposal early. The 14-day cool-down attaches to the "aggregator design" topic, not to corpus capture — but jumping from corpus to aggregator before K=10 needs explicit justification.

4. **The proposal flow's cool-down was designed for code/prompt changes. This proposal is a process commitment.** If the operator wants to revise the corpus protocol (change K, change capture script behavior) inside the cool-down window, that's a small revision that should not trigger a new full proposal. But it should be explicitly noted in this proposal's update log.

## Approval

(To be filled by user when merging or rejecting.)
