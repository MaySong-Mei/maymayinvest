# Proposal: Relabel CASE_3_AMBIGUOUS expected_verdict from `ambiguous` to `right_bet`

**Date**: 2026-05-23
**Author**: claude-code-operator (proposed); dialogue reviewer `ab5e8f0e1cd382d43` (recommended)
**Artifact**: `v1/backend/tests/eval/reviewer_eval_set.py` — `CASE_3_AMBIGUOUS.expected_verdict`, name, and rationale text
**Cool-down expires**: 2026-06-06 (14 days)

## What changes

Three changes to one fixture, all in `v1/backend/tests/eval/reviewer_eval_set.py`:

1. `CASE_3_AMBIGUOUS.expected_verdict`: `"ambiguous"` → `"right_bet"`
2. Variable name: `CASE_3_AMBIGUOUS` → `CASE_3_SOUND_NO_ACTION_UNDER_AMBIGUITY`
   (parallels `CASE_5_NO_ACTION_RIGHT`; the "no-action under thin info" structural pattern becomes visible)
3. The fixture's case name (the string `name="case-3-legitimately-ambiguous"`) → `name="case-3-sound-no-action-under-ambiguity"`
4. `rationale_for_expected` rewritten to reflect the corrected taxonomy: the **situation** is ambiguous (information is thin), but the **decision** is a right bet (sound process, honest uncertainty acknowledgment, no-action matched to confidence). This explicitly parallels CASE_5_NO_ACTION_RIGHT.

## Why

The reviewer (prompt `v1-2026-05-22`) produced `right_bet` on this fixture across 3 independent attempts with substantively congruent reasoning:

| attempt | verdict | confidence | source |
|---|---|---|---|
| 1 (main eval) | right_bet | 0.82 | `reviewer-v1-2026-05-22-2026-05-23-results.json` |
| 2 | right_bet | 0.82 | `reviewer-v1-2026-05-22-case3-consistency-2026-05-23.json` |
| 3 | right_bet | 0.88 | same file |

All three reasoning chains converge on the same taxonomic argument:

> "Sound process applied honestly to ambiguous information yields a right bet, not an ambiguous one. The `ambiguous` verdict should be reserved for cases where the reviewer themselves is unsure whether the process was sound."

This is a useful taxonomic clarification consistent with PHILOSOPHY.md's process-based framing:
- "Situation is ambiguous" — about the world (information is genuinely thin)
- "Decision is ambiguous" — about decision quality (process soundness is unclear)

Case 3's dossier exhibits the former (thin info on CEO departure reason), with sound process: alternatives weighed, probe rejected on cognitive-cost grounds, short rejected as reflexive bear bias, wait-and-see chosen with concrete trigger conditions. The reviewer's read — that this is right_bet under situation-ambiguity, not ambiguous-decision — is consistent with how CASE_5_NO_ACTION_RIGHT is structured (sound no-action with portfolio-concentration reasoning is right_bet despite producing no order).

The fixture's original `rationale_for_expected` already conceded: *"A reviewer who verdicts right_bet is also defensible (process matches information)."* The operator was reasoning about the world-state (thin info → ambiguous) rather than the decision-state (sound process → right bet) when authoring the label. The reviewer's three-attempt convergence operationalizes this pre-conceded ambiguity.

## Metric expected to move and direction

After this relabel, the next reviewer eval pass should:
- 5/5 PASS (assuming reviewer's verdict-level behavior is stable on the other 4 cases)
- Avg confidence on right_bet verdicts stays in the 0.78–0.88 range observed so far
- No new flags introduced as a result of the relabel (the dossier text doesn't change)

If instead the next pass shows reviewer drift on case 3 (e.g. some attempts now return ambiguous), the relabel may have been premature. Falsification path below.

## Falsification

This relabel is wrong if **any one of**:

1. A v2 reviewer prompt (when authored) independently verdicts `ambiguous` on this fixture with a substantive argument that decision-ambiguous is the right read.
2. 2+ different reviewer implementations (e.g. ClaudeAPIReviewer when built, or Ollama-backed reviewer) split between `ambiguous` and `right_bet` on this fixture.
3. The same v1 reviewer's verdict on case 3 drifts in a future eval run (e.g. ≥1 `ambiguous` in next 5 trials).

If any of these occur within 6 months, the relabel should be REVERTED via a new proposal, and the fixture either retired or split into two cases (one situation-ambiguous-right-bet, one decision-ambiguous) rather than locked to either label.

## Alternatives considered

1. **Keep `ambiguous` label, treat reviewer disagreement as noise.** Rejected: 3/3 consistent with similar reasoning chains, confidence ramping upward (0.82, 0.82, 0.88). This is not noise.

2. **Add a fourth verdict category** ("right_bet_under_ambiguity" or similar). Rejected: complicates the taxonomy unnecessarily; the reviewer's existing 3-category distinction is sound if applied consistently to *decision quality* rather than *information state*.

3. **Author a new case for true decision-ambiguity** (where the reviewer would genuinely be unsure if the process was sound) and keep case 3 as `right_bet`. **Partially accepted**: this is captured in the risks section as a follow-up.

4. **Wait for more data before changing anything.** Rejected: 3 attempts is the state-machine threshold; per PHILOSOPHY.md the silent-retry path is now closed. Either propose-change or escalate-to-human is the next move.

## Reviewer judgment

**Dialogue reviewer** (subagent `ab5e8f0e1cd382d43`, invoked 2026-05-23 after the 3-attempt consistency check) recommendation: **propose-change** at confidence 0.72.

Key reasoning (excerpted):
- The reviewer's category split (situation- vs decision-ambiguous) "aligns directly with the project's core framing in PHILOSOPHY.md."
- "A spec-gaming reviewer would systematically push toward `right_bet` even when process was weak; here, the reviewer hit wrong_bet on case 2 and case 4 (including the adversarial polished-but-bad case), so it is not generically lenient."
- "The mechanism of disagreement is stable [across 3 attempts], which is what matters for goal-side calibration."
- "The fixture's own rationale already conceded ambiguity, so this is unwinding a documented hedge, not overriding a confident operator stance. The pattern to watch is *future* relabels without pre-conceded uncertainty in the original rationale — those should be treated with much more suspicion."

The dialogue reviewer is architecturally one-shot for this case and is not eligible to be used as a verdict reviewer afterward (per PHILOSOPHY.md state machine).

## Risks

1. **Anchoring future evals to one reviewer's taxonomy on a 3-trial sample.** If the v1 reviewer prompt has a subtle bias, this relabel cements it. Mitigation: when a second reviewer implementation (ClaudeAPIReviewer or Ollama-backed) is built, re-test this case immediately. If it splits, revert.

2. **Loss of a true `ambiguous` exemplar.** v1 eval set after this change has zero cases expected to verdict `ambiguous`. The reviewer's behavior on the `ambiguous` verdict path will be untested. Follow-up: author a new case where the *decision quality itself* is hard to call (not just the information). This is a separate proposal.

3. **Spec-gaming precedent.** "Reviewer disagrees → relabel" is exactly the pattern PHILOSOPHY.md warns against. This particular relabel is defensible because:
   - The original rationale pre-conceded right_bet was defensible
   - The dialogue reviewer is a separate subagent that recommended
   - The proposal+approval flow is being honored (this file exists)
   - The structural parallel to case 5 is identifiable independently of the reviewer

   Future relabels without these properties — especially relabels of cases whose original rationale was confident — should face higher scrutiny.

## Approval

(To be filled by user when merging.)
