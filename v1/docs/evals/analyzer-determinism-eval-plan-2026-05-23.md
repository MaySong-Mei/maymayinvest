# Pre-registered analysis plan: ClaudeCodeAnalyzer determinism

**Filed**: 2026-05-23
**Author**: claude-code-operator
**Status**: pre-registration. **Filed before any trials are run** to prevent HARKing.
**Plan reviewed by**: (optional, see Reviewer judgment below)

This document defines how the operator will analyze the output of an analyzer-determinism experiment **before** running the experiment. Per the dialogue reviewer's 2026-05-23 guidance (commit `b53075b`), this is the lightweight equivalent of the proposals/ flow for non-proposal investigations.

The corresponding trials and analysis will be committed in a **separate** commit. This plan is not allowed to change once the trials are in progress.

## Background

Two runs of `ClaudeCodeAnalyzer` over the AAPL 2024-05-02 buyback event, with the same prompt + same event payload + same snapshot, produced structurally different dossiers (commit `5ae95c3` and `b53075b`). Same stated confidence (0.6), different mode (dry_run vs notify), different intent (BUY 2 vs null). This raised the question: how noisy is the analyzer's output across repeated trials of the same input?

## Experiment design

### Inputs (fixed across all trials)

- **Event**: `tests/fixtures/edgar_8k_aapl_buyback_2024.json` (the hand-curated AAPL 2024-05-02 fixture)
- **Snapshot**: empty portfolio + AAPL last_price set to `Decimal("220.50")` (we keep the stale price for THIS experiment because run-1 and run-2 used it; comparability requires same input. The dev seed has been cleaned in commit `1e9bd92` for future use but is being explicitly recreated here as part of the test setup.)
- **Analyzer prompt**: `v1-2026-05-23` (current; unchanged)
- **Subprocess timeout**: 120s per trial
- **Concurrency**: trials run serially (no race / shared state confound)

### N

**N = 5** trials. This is the operator's first experiment characterizing analyzer determinism. 5 is small enough to be cheap (~5 claude calls, ~$0.50 of subscription budget) and large enough to distinguish "every run identical" from "structurally different outputs."

If results are borderline (see decision rules below), the operator may file a follow-up plan for N=10 or N=20 — but this commit is N=5. No mid-experiment extension.

### Run-to-run variables observed (output features)

For each of the 5 trials, the operator records:
- `mode` ∈ {notify, dry_run, auto}
- `proposed.intent is null` (boolean: action vs no-action)
- if intent present: `(symbol, side, qty, type)` tuple
- `confidence` (decimal)
- count of `alternatives_considered`
- count of `skills_invoked`
- `latency_ms`
- first 200 chars of `reasoning_chain` (for qualitative comparison)

These are pre-specified outcome features. The operator commits to looking at THESE features and these alone for the headline conclusion. (Qualitative reasoning differences may be noted in prose but are not the basis for the determinism verdict.)

## Outcome bins (pre-registered)

After the 5 trials, the operator will assign the result to **exactly one** of these four bins. The operator commits in advance to use these specific definitions, NOT to invent a new bin after seeing the data.

### Bin 1: "Deterministic enough to ship"
- All 5 trials agree on `mode`
- All 5 trials agree on `proposed.intent is null`
- If all 5 propose an intent: all 5 agree on (symbol, side); qty range satisfies `max(qty) <= 1.5 * median(qty) AND min(qty) >= 0.5 * median(qty)` (median = the 3rd value when the 5 qty values are sorted)
- `confidence` sample standard deviation (`statistics.stdev`, Bessel-corrected N-1) `< 0.1`

Interpretation: analyzer output is stable enough that production runs can use N=1 per event with confidence the result reflects the analyzer's "real" view.

### Bin 2: "Noisy on numerics, stable on action"
- All 5 trials agree on `mode` AND `proposed.intent is null`
- If intent present: all 5 agree on (symbol, side); EITHER qty range fails the bin-1 criterion (`max > 1.5*median` OR `min < 0.5*median`) OR `confidence` stdev (N-1) `>= 0.1`

Interpretation: the analyzer's core decision (act vs no-act, direction) is stable, but sizing/calibration is noisy. Production runs should use N=1 for the action decision but treat the specific qty/confidence as approximate. The state-machine threshold (N<3 silent retries) is appropriate for the numeric details.

**Action cost for bin 2** (added 2026-05-23 per reviewer ad2b90c4c8f1f4cd7 defect #7): in addition to documenting the noise band, the operator MUST file a proposal to add `analyzer_noise_floor` metadata to DecisionDossier (e.g. a `qty_uncertainty_band` and `confidence_uncertainty_band` field with the empirical bounds from this experiment). This makes bin 2 carry a real cost: a documented noise band that future analyzer changes must defend against.

### Bin 3: "Stochastic on decision"
- Trials disagree on `mode` (the 5 mode values are not all identical) OR on `proposed.intent is null` (the 5 boolean values are not all identical)
- Disagreement is at the **decision** level, not the **numeric** level (numeric-only disagreement is bin 2)
- Number of distinct `(mode, intent_is_null)` patterns across the 5 trials is **exactly 2**

If number of distinct `(mode, intent_is_null)` patterns is **3 or more**, this triggers bin 4 instead (see priority order below).

**Tie-break for N=5 mode majority**: if no `mode` value appears in 3+ trials (e.g. mode = `[notify, notify, dry_run, dry_run, auto]`), this counts as a 3-distinct-pattern situation and falls into bin 4, not bin 3.

Interpretation: the analyzer's core decision is unstable but converges to one of 2 patterns. Production runs cannot rely on N=1; the system must persist multiple analyses per event and aggregate (vote? show all? defer to reviewer?) before acting. This is the case the goal state machine was designed for and the most likely outcome based on the N=2 we already have.

### Bin 4: "Unusable as-is"
- 3 or more distinct `(mode, intent_is_null)` patterns across 5 trials
- OR: ≥1 trial produces a parse-error from the analyzer (the JSON output fails schema validation per `_parse_dossier_json` in `app/intel/analyzer/claude_code.py`)
- OR: ≥1 trial produces a subprocess error (non-zero exit code, timeout) — separate from a parse error
- (the "internally incoherent" clause from the original draft has been REMOVED per reviewer ad2b90c4c8f1f4cd7 defect #4 — it was a freebie escape hatch. If a future experiment wants to test internal coherence, that's a separate pre-registered experiment with its own taxonomy of "what counts as incoherent".)

Interpretation: the analyzer prompt v1-2026-05-23 isn't producing reliable output. Either the prompt needs rework (file a proposal for v2) or the temperature/seed settings need investigation, or the input is genuinely too thin to support useful analysis.

## Bin assignment priority order (added 2026-05-23 per reviewer defect #9)

If the dataset could match multiple bin definitions, the operator assigns the HIGHEST-firing bin:

**Bin 4 > Bin 3 > Bin 2 > Bin 1**

That is: if any bin-4 trigger fires (parse/subprocess error, or ≥3 distinct decision patterns), the verdict is bin 4 — even if the remaining trials would have qualified as bin 1. This biases assignment AWAY from "deterministic enough" when there are signs of trouble, which is the conservative direction.

## Failed-trial handling (added 2026-05-23 per reviewer defect #8)

If a trial fails to produce a valid dossier:
- **Subprocess error (timeout, non-zero exit)**: counts as bin-4 trigger. The trial is INCLUDED in the count of 5 (do not run a replacement trial; the failure is informative).
- **JSON parse error**: counts as bin-4 trigger. Same — included in the 5, not replaced.
- **Network unavailable / claude binary missing / OAuth token expired**: NOT counted as analyzer noise. Operator pauses experiment, fixes the environment, then restarts the entire experiment with 5 fresh trials. Document the environment failure in the writeup but it does NOT inform the determinism question.

## Decision rules (what the operator will do based on the bin)

| bin | next operator action |
|---|---|
| 1 | Treat analyzer as deterministic; move to D (EDGAR poller) next. Defer B and C. |
| 2 | Document the noise floor on qty/confidence. Move to D (EDGAR poller) next. Defer B; consider C (structured fields would let aggregation be done at the schema level). |
| 3 | DO NOT move to D yet. The system needs a multi-analysis-per-event aggregation strategy. Operator files a proposal for that, which is itself an A-tier finding. B and C are deferred until aggregation strategy is settled. |
| 4 | DO NOT move to D yet. Operator files a proposal for analyzer prompt v2. This is an analyzer-prompt cool-down trigger; subsequent reviewer-prompt-change work is on hold during the cool-down window. |

## What the analysis writeup will look like

After the trials, the operator will write `v1/docs/evals/analyzer-determinism-results-2026-05-23.md` containing:

1. A table of the 5 trials' outcome features (the variables listed above)
2. The bin assignment (one of 1-4)
3. The decision (one of the rows above)
4. Raw JSON output saved to `v1/docs/evals/analyzer-determinism-results-2026-05-23.json`

The operator commits to writing the bin assignment **before** writing the qualitative reasoning. That is, the table goes first, then the bin name, then the prose — not the other way around. Writing prose first lets the operator's qualitative read color the bin choice; writing the bin first commits to the empirical rule.

## Pre-registered honesty controls

1. **No bin invention.** Outcome must fit into one of bins 1-4 above. If the data genuinely doesn't fit any (and not just "I want to claim something else"), the operator must file a follow-up plan, not extend the bin definitions inline.

2. **No mid-experiment changes.** If trial 3 produces a surprising result, the operator does not stop at N=3 and call it. The full N=5 is committed to up front.

3. **No selective qty reporting.** All 5 trials' qty (if present) go in the table, not just the ones that fit a narrative.

4. **Cost transparency.** Total cost (token estimate or subscription draw note) is included in the writeup.

5. **The plan is fixed.** This file is the contract. If after the experiment the operator believes the plan was wrong, the lesson goes in a follow-up plan for the NEXT experiment, not as an edit to this file.

## What this plan does NOT cover

- The analyzer's behavior on **different events** (this is N events fixed at 1; varying events is a separate question)
- The reviewer's behavior on the resulting dossiers (this is analyzer-side only)
- Whether the analyzer is "correct" — only whether it is **stable**

## Reviewer judgment

**Dialogue reviewer**: subagent `ad2b90c4c8f1f4cd7`, invoked 2026-05-23 after the initial draft of this plan was written.

**Verdict**: "approve, run after fixing defects" at confidence 0.72.

**Findings (paraphrased)**:
- Plan's spine is right; structural defenses (bin pre-commitment, write-table-before-prose, fixed N, no mid-experiment extension) close common HARKing avenues
- BUT 4 defects required fixing before run:
  1. Bin 1 "qty within 50% range of median" was mathematically ambiguous at N=5 → **FIXED**: now `max <= 1.5*median AND min >= 0.5*median`
  2. Bin 4's "internally incoherent" clause was an operator-judgment escape hatch → **FIXED**: removed; bin 4 fires only on parse/subprocess errors or ≥3 distinct decision patterns
  3. N=5 tie-breaking under 2-2-1 mode splits was undefined → **FIXED**: 2-2-1 splits = "3 distinct" = bin 4 trigger
  4. Multi-bin ties had no priority → **FIXED**: explicit Bin 4 > Bin 3 > Bin 2 > Bin 1 priority section added

**Other improvements applied**:
- Confidence stdev definition pinned to `statistics.stdev` (Bessel-corrected, N-1)
- Bin 2 now carries a real action cost (proposal to add `analyzer_noise_floor` metadata) per defect #7
- Failed-trial handling (defect #8) added: subprocess/parse errors are bin-4 triggers; environment failures restart the experiment

**Defects NOT addressed in this revision**:
- Defect #6 (prose-writing handed off to fresh subagent) was deemed nice-to-have. If pattern-completion shows up in the writeup despite the table-first rule, future plans should incorporate this.

**Operator's verdict on the verdict**: accept all critical fixes; plan is now run-ready. The fix itself took ~30 minutes as the reviewer estimated.

The pre-registration is locked at this point. No further edits to this file once trials start.
