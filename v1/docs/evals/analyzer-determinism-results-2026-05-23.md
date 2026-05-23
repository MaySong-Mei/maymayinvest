# Analyzer determinism experiment: results

**Date**: 2026-05-23
**Pre-registered plan**: [`analyzer-determinism-eval-plan-2026-05-23.md`](analyzer-determinism-eval-plan-2026-05-23.md) (commit `90e4db1`, locked)
**Raw output**: [`analyzer-determinism-results-2026-05-23.json`](analyzer-determinism-results-2026-05-23.json)
**N**: 5 trials, serial, 172.5 s total wall time, ~$0.20-0.40 subscription draw
**Analyzer prompt version**: `v1-2026-05-23`

This writeup follows the pre-registered structure: table first, bin assignment computed mechanically from locked rules, prose last. The operator did NOT read the `reasoning_first_200_chars` field or any qualitative content before writing the bin assignment.

## Step 1: outcome features (table)

| trial | mode | intent_is_null | confidence | alt_count | skills | latency_ms | qty | side | type |
|---|---|---|---|---|---|---|---|---|---|
| 1 | dry_run | false | 0.62 | 5 | 0 | 36360 | 1 | buy | market |
| 2 | notify | true | 0.62 | 4 | 0 | 30062 | — | — | — |
| 3 | dry_run | false | 0.62 | 5 | 0 | 39202 | 2 | buy | limit |
| 4 | dry_run | false | 0.60 | 4 | 0 | 33047 | 1 | buy | market |
| 5 | notify | true | 0.65 | 5 | 0 | 33860 | — | — | — |

## Step 2: bin assignment (mechanical computation from locked rules)

**Pre-checks**:
- Subprocess errors: 0
- Parse errors: 0
- Environment failures: 0
- → No bin-4 trigger from errors

**Decision pattern** `(mode, intent_is_null)` per trial:
- 1: (dry_run, false)
- 2: (notify, true)
- 3: (dry_run, false)
- 4: (dry_run, false)
- 5: (notify, true)

**Distinct decision patterns**: 2 (dry_run+false ×3, notify+true ×2)

**Pattern-multiplicity check (bin 4 from pattern count)**: 2 < 3 → does NOT fire.

**Bin 1 check** (all 5 trials agree on mode AND intent_is_null):
- mode values: 3× dry_run, 2× notify → NOT all identical
- → bin 1 fails.

**Bin 2 check** (all 5 trials agree on mode AND intent_is_null, with possible numeric noise):
- Same mode/intent_is_null criterion as bin 1 → NOT satisfied.
- → bin 2 fails.

**Bin 3 check** (trials disagree on mode OR intent_is_null; exactly 2 distinct (mode, intent_is_null) patterns; majority exists):
- Disagreement on mode: yes (3-2 split)
- Disagreement on intent_is_null: yes (3-2 split)
- Distinct patterns: 2 ✓
- Tie-break for N=5: majority is "dry_run+false" with 3 trials (not 2-2-1; no tie problem)
- → **bin 3 fires.**

**Bin 4 check** (≥3 distinct patterns OR error from analyzer):
- 2 distinct patterns < 3 → does NOT fire from pattern count.
- 0 errors → does NOT fire from errors.
- → bin 4 does NOT fire.

**Priority order**: Bin 4 > Bin 3 > Bin 2 > Bin 1.
- Bin 4 did not fire.
- Bin 3 fires.

## Step 3: BIN ASSIGNMENT

**BIN 3 — "Stochastic on decision"**

## Step 4: pre-registered decision rule for bin 3

From the locked plan:
> Bin 3 → DO NOT move to D yet. The system needs a multi-analysis-per-event aggregation strategy. Operator files a proposal for that, which is itself an A-tier finding. B and C are deferred until aggregation strategy is settled.

## Step 5: prose discussion (written LAST)

Now the operator may discuss what the data says. Bin 3 is already locked in; no qualitative observation in this section can change it.

### What the data shows

The analyzer is **structurally non-deterministic on the decision-level output for this event**. Across 5 trials with identical inputs:

- **Action vs no-action split is 3:2**. Three trials proposed an order (BUY AAPL, 1-2 shares); two trials chose notify-only and refused to size.
- **Stated confidence is essentially constant** at 0.60-0.65 regardless of which decision is reached. The analyzer's self-reported confidence does NOT distinguish "I am proposing an action" from "I am refusing to act." Calibration is, in this respect, broken at the decision boundary.
- **Among the 3 acting trials**: 2 propose 1 share (market), 1 proposes 2 shares (limit). qty range 1-2; median 1. Computing the bin-1 numeric criterion: `max(qty)=2`, `1.5 * median = 1.5`, `2 > 1.5` → would fail bin-1 numeric criterion even if mode had been consistent. But that's moot — mode wasn't consistent, so we never reached the numeric check.
- **Latencies cluster 30-39 s**, all sub-minute. Cost is bounded.
- **Alternatives counts 4-5** across all trials — analyzer reliably considers 4+ alternatives whether it acts or not. This part of the prompt is robust.

### Implications (per the pre-registered decision rule)

1. **Single-run analyzer eval is structurally insufficient.** A production pipeline that takes one analyzer call per event will, in this kind of event class, take action 60% of the time and refuse 40% of the time, even though the "right" answer (whatever it is) should be one of the two. This is unacceptable for a system meant to support process-based supervision.

2. **The system needs a multi-analysis-per-event aggregation strategy.** The schema already supports it — `decisions.event_id` is non-unique by design. What's missing is a code path that runs N analyses, persists all N, and decides what to surface (vote? show all candidates to the reviewer? defer to the human?). This is itself a non-trivial design choice and is the natural next proposal.

3. **B (reviewer prompt v2 with internal-consistency check) and C (structured `confirmation_criteria`/`invalidation_criteria` fields) remain deferred.** Both could land in the wrong place if we don't first know how the analyzer's instability should be handled. For example: if aggregation involves the reviewer judging multiple candidate dossiers, that changes what the reviewer prompt needs to do.

4. **D (EDGAR poller) remains deferred.** Broadening to multiple events when the system can't yet decide whether to act on one event is the wrong direction.

### What the data does NOT show

- **Whether the analyzer is non-deterministic on different events.** N=1 event. Conceivable a different event class (e.g. routine 10-Q with low decision-relevance) would produce deterministic refusals. We don't know yet.
- **Whether the underlying issue is prompt design, model temperature, or input ambiguity.** All three are plausible. The 8-K event itself is genuinely close-to-the-line: there are valid reasons to act (structural buyback signal) AND valid reasons to wait (post-close, no confirmation). It's not surprising the analyzer doesn't always pick the same side.
- **Whether the second-run dossier (which scored `right_bet` 0.85 from the reviewer in commit `b53075b`) is representative or unusual.** The 5 new trials suggest "notify + no intent" is the minority outcome, but the reviewer endorsed it strongly. The action trials might have scored lower from the reviewer — but that's a downstream eval, not this one.

### What about the dialogue reviewer's defect #7?

The plan's bin 2 was modified to require filing an `analyzer_noise_floor` proposal as a real cost. This experiment landed in bin 3, not bin 2, so that requirement does not bind here. The implication: the analyzer's noise is at the **decision** level, not the **numeric** level — addressing the decision-level noise (via aggregation) is more important than documenting numeric noise.

### What about the dialogue reviewer's defect #6?

The plan noted that prose should ideally be written by a fresh-context subagent given only the table. That was deemed nice-to-have and not implemented in this revision. The prose above was written by the same operator who saw the trials run. The operator believes the table-first / bin-first discipline carried the load, but a future operator should consider implementing defect #6 if pattern-completion shows up in writeups.

### Operator confidence in this writeup

0.85. High because (a) the bin assignment is mechanically forced by the locked rules and (b) the prose was written after the bin was set. The remaining 0.15 reflects: N=1 event limits how broadly we can generalize; the underlying event itself is genuinely borderline so a stable analyzer might still split on it; the next decision (aggregation proposal) involves design choices that this experiment does not directly inform.

## Cost summary

- 5 × ~35s analyzer subprocess calls
- Total wall time: 172.5s
- Subscription draw: ~$0.20-0.40 (rough estimate; CLAUDE_CODE_OAUTH_TOKEN draws against Pro/Max inference quota, not API credits)
- Operator time for analysis + writeup: ~25 min (most of it spent NOT looking at the prose before bin assignment)

## Next step

File a proposal to design a multi-analysis-per-event aggregation strategy. The locked decision rule for bin 3 makes this the required next action; the operator does not have discretion to skip it.

Proposal will be at `v1/docs/proposals/2026-05-23-multi-analysis-aggregation-strategy.md` in a subsequent commit.
