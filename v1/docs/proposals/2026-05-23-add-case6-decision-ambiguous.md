# Proposal: Add CASE_6 — a true decision-ambiguous fixture

**Date**: 2026-05-23
**Author**: claude-code-operator (proposed); awaiting dialogue reviewer + human approval
**Artifact**: `v1/backend/tests/eval/reviewer_eval_set.py` — adds a new `CASE_6_DECISION_AMBIGUOUS` constant and adds it to `ALL_CASES`
**Cool-down expires**: 2026-06-06 (14 days)

## Context — the gap this fills

After the case-3 relabel (merged in commit `8ad69eb`), the v1 eval set contains zero fixtures expected to verdict `ambiguous`. The reviewer's behavior on the `ambiguous` verdict path is therefore empirically untested.

The verdict reviewer reserved `ambiguous` for "cases where the reviewer themselves is unsure whether the process was sound" — i.e. **decision-quality ambiguous**, not just information-thin. This proposal adds a fixture intended to exercise that path.

## What changes

Add one new `EvalCase` constant and append it to `ALL_CASES`. No other fixtures are modified. No other code changes.

## Draft fixture text (subject to dialogue reviewer + human input before merge)

```python
# ============================================================================
# CASE 6: DECISION-AMBIGUOUS (intentional reviewer hard-case)
# ============================================================================
# Information is ADEQUATE (earnings beat is real, guidance is real, prices
# are concrete). The decision quality, however, is hard to call:
#
#   - Reasoning chain has a thin "long-term thesis intact" justification
#     without spelling out what the thesis is
#   - "Market regime is supportive" is asserted but not analyzed
#   - The "wait for pullback" alternative is rejected with "might not come"
#     — that's true for momentum stocks but also reads as FOMO rationalization
#   - Confidence 0.65 is neither obviously calibrated nor obviously not
#   - Sizing is moderate (5% of cash), not absurd in either direction
#
# A reviewer should plausibly verdict either right_bet OR wrong_bet here
# depending on how strictly they read the "thesis intact" hand-wave. The
# `ambiguous` verdict applies when the reviewer concludes they genuinely
# cannot tell from the dossier alone whether the process was sound.
#
# If the reviewer consistently verdicts one direction with substantive
# reasoning, that itself is informative — it suggests `ambiguous` is a
# narrower category than the operator currently expects.

CASE_6_DECISION_AMBIGUOUS = EvalCase(
    name="case-6-decision-ambiguous",
    expected_verdict="ambiguous",
    rationale=(
        "Information is adequate, not thin. The decision quality itself is "
        "what's hard to judge. The reasoning chain leans on two unexamined "
        "claims ('long-term thesis intact' and 'market regime supportive') "
        "without unpacking either. Alternatives are listed but the rejection "
        "of 'wait for pullback' could read as sound (momentum often doesn't "
        "pull back) or as FOMO-driven (the operator wants to act). Confidence "
        "0.65 is in the calibration grey zone — neither clearly right (would "
        "be 0.7-0.8 if the thesis were spelled out) nor clearly wrong (would "
        "be 0.5 if the operator acknowledged the hand-waves). A reviewer who "
        "verdicts right_bet by giving the operator credit for sober sizing "
        "and explicit alternatives is defensible. A reviewer who verdicts "
        "wrong_bet by flagging the unexamined claims as 'reasoning_doesnt_"
        "justify_confidence' is also defensible. The expected verdict here "
        "is `ambiguous` because a careful reviewer should notice that they "
        "cannot tell which read is correct from the dossier alone."
    ),
    expected_flags_subset=[
        # These are flags a reviewer COULD raise on either side. Listing them
        # as expected_subset means "if reviewer raises any of these, the
        # reviewer is engaging with the right tension." The verdict path
        # (right_bet vs wrong_bet vs ambiguous) is the harder test.
        "reasoning_doesnt_justify_confidence",
        "information_insufficient_for_decision",  # arguably wrong category, but a reviewer might use it
    ],
    dossier=DecisionDossier(
        actor_id="hand-crafted-fixture",
        event_id="rss:business-wire-2026-05-22-mid-cap-earnings",
        event_kind="rss_business_wire",
        event_summary="MidCorp Q1 EPS beats by 12%, FY guidance raised; stock +8% after hours",
        available_info_snapshot={
            "event_payload": {
                "headline": "MidCorp reports Q1 EPS of $1.42 vs consensus $1.27; raises FY guide from $5.40 to $5.80",
                "body_excerpt": (
                    "MidCorp Inc. (MIDC) today reported Q1 EPS of $1.42, "
                    "beating consensus of $1.27 by 12%. Revenue of $487M "
                    "exceeded the $470M consensus. The company raised full-year "
                    "EPS guidance to $5.80, up from prior $5.40. CFO cited "
                    "'continued operational efficiency and stronger pricing "
                    "discipline' as primary drivers."
                ),
                "ticker": "MIDC",
            },
            "recent_prices": {
                "MIDC_1d_close": [88.20, 88.50, 87.90, 88.10, 88.30],
                "MIDC_aftermarket_last": 95.30,
                "MIDC_avg_daily_volume": 1_200_000,
                "SPY_1d_close": [555.20, 556.10, 556.80, 557.10, 557.30],
                "SPY_intraday_last": 557.40,
            },
            "portfolio": {
                "cash": "98000.00",
                "positions": [],
                "buying_power": "98000.00",
            },
            "context": {
                "market_session": "post_market",
                "extended_hours_available": True,
                "earnings_calendar_position": "in season, mid-cap industrials reporting now",
            },
        },
        reasoning_chain=(
            "MidCorp's beat is clean — both top and bottom line, plus guidance "
            "raise. The long-term thesis is intact, so adding here is consistent "
            "with our exposure plan. Market regime is supportive (SPY firm, no "
            "obvious risk-off signal in the tape), so the macro background "
            "isn't fighting us. Right-side approach is to buy on next-session "
            "open, capturing the structural beat without paying after-hours "
            "premium where liquidity is thin and slippage is unpredictable.\n\n"
            "Sizing: 50 shares at projected open ~$94 = ~$4700 notional. "
            "About 4.8% of cash. Within position size norms; not full-conviction "
            "but not a probe either.\n\n"
            "Confidence 0.65: the earnings beat is real and the guide raise is "
            "material, so directional confidence is moderately high. The chase "
            "into a +8% AH move tempers it — we are not getting a discount."
        ),
        alternatives_considered=[
            AlternativeConsidered(
                action="wait for pullback (intraday or 1-2 day)",
                rejected_because=(
                    "momentum stocks post-beat often don't pull back; waiting "
                    "for a discount that doesn't arrive is itself a cost"
                ),
            ),
            AlternativeConsidered(
                action="buy half size now, half on pullback",
                rejected_because=(
                    "operational complexity for the position size; the half-"
                    "and-half plan dilutes both the conviction expression and "
                    "the discount-capture, doing neither well"
                ),
            ),
            AlternativeConsidered(
                action="no action (pass)",
                rejected_because=(
                    "the beat + raise is exactly the catalyst the thesis was "
                    "waiting for; passing on this would be inconsistent with "
                    "the thesis being held"
                ),
            ),
        ],
        confidence=Decimal("0.65"),
        skills_invoked=[
            SkillInvocation(
                name="earnings_beat_raise_pattern",
                version="0.1.0",
                args_summary="ticker=MIDC, beat_pct=12, guide_raise=true",
            ),
        ],
        proposed=ProposedOrder(intent=_intent("MIDC", OrderSide.BUY, "50")),
        mode="dry_run",
        latency_ms=2900,
    ),
)
```

## Why this fixture probably tests decision-ambiguity

Specific tension points the dossier introduces:

1. **"Long-term thesis intact"** without saying what the thesis is. A strict reviewer flags `reasoning_doesnt_justify_confidence`; a lenient reviewer reads this as shorthand referring to context not shown in the dossier. Both readings are defensible.

2. **"Market regime supportive"** with one-line evidence (SPY firm). A strict reviewer wants regime analysis; a lenient one accepts "macro not fighting us" as adequate when the trade is single-name catalyst-driven.

3. **"Wait for pullback" rejection** is correct for momentum stocks (true positive base rate) and convenient FOMO defense (true rationalization risk). Same words, two readings.

4. **Confidence 0.65** is exactly in the zone where calibration is unprovable from the dossier alone.

5. **Sizing 4.8%** is sober — not the polished-but-bad case 4 pattern (which was small size + confident reasoning + invented fact). Here the size matches a moderate-confidence call, but the reasoning's specificity is below the size warrants.

A reviewer who concludes "I cannot tell whether the operator has a substantive thesis they didn't fully document, or whether they are dressing up FOMO" should verdict `ambiguous`. A reviewer who picks a side firmly is doing one of:
- correctly seeing one side dominates (and the fixture should be relabeled)
- pattern-matching on something the operator didn't intend

Either outcome is informative.

## Metric expected to move and direction

Three possible outcomes on the first eval pass after this fixture is added (run 3 times for state-machine consistency):

| pattern | interpretation | next step |
|---|---|---|
| reviewer consistently `ambiguous` (3/3) | `ambiguous` is a real verdict path; fixture works | keep as-is |
| reviewer consistently `right_bet` (3/3) with substantive reasoning | reviewer reads `right_bet` more liberally than the operator expects | new proposal: relabel to `right_bet` |
| reviewer consistently `wrong_bet` (3/3) with substantive reasoning | reviewer is stricter than the operator expects | new proposal: relabel to `wrong_bet` |
| split (e.g. 1 ambiguous, 1 right_bet, 1 wrong_bet) | reviewer is genuinely uncertain — fixture IS decision-ambiguous | keep as-is; this is the desired result |

Outcomes 2 and 3 each constitute legitimate empirical findings about the reviewer's category boundaries. Outcomes 1 and 4 both validate that the `ambiguous` verdict is reachable.

## Falsification

This fixture is wrong if a strict structural reading shows it actually telegraphs one side. Specifically, this proposal is wrong if:

1. Three reviewer attempts produce the same verdict (not `ambiguous`) with the same dominant reasoning. That would mean the dossier isn't genuinely tension-laden; it just looks ambiguous to the operator.
2. The dialogue reviewer judging this proposal independently concludes the fixture reads strongly one direction.

In either case, the fixture should be retired or substantially rewritten, not just relabeled.

## Alternatives considered

1. **Author a "thesis spelled out" version** (decision becomes clearly right_bet). Rejected — that's just CASE_5 with different content; doesn't fill the gap.

2. **Author a "thesis hand-waved + bad sizing" version** (decision becomes clearly wrong_bet). Rejected — that's just CASE_2 with different content.

3. **Author a fixture where the operator's reasoning is incomplete but salvageable**. Accepted — this is the version above. The tension is structural: same dossier reads differently depending on reviewer strictness.

4. **Wait until a real (non-stub) analyzer is producing dossiers, then pick a real one to label.** Rejected — that's a Phase 2 improvement, but for v1 we need at least one decision-ambiguous case for verdict-path coverage. Better to hand-craft now and retire/refine when real dossiers are available.

## Reviewer judgment

**Dialogue reviewer**: subagent `a67350f3185d0fae1`, invoked 2026-05-23.
**Recommendation**: **B — relabel to `right_bet`** OR **withdraw proposal entirely**.
**Reviewer confidence**: 0.7.

### Verdict-reviewer pass (subagent acting as v1-2026-05-22 reviewer)

When given the dossier text alone (no expected_verdict, no rationale), the subagent verdicted **`right_bet`** at confidence 0.68. Reasoning excerpts:

> "The event is a clean, hard catalyst: EPS beat 12%, revenue beat, FY guide raised ~7.4%. The operator is not chasing a thin signal."
>
> "Process check: alternatives are present and substantive — three distinct ones, each with a non-trivial rejection. None of these rejections collapse to 'the news is positive, so buy' (the case-2 failure mode)."
>
> "Sizing check: ~4.8% of cash, framed as 'not full-conviction but not a probe' — sizing matches the moderate 0.65 confidence. Compare to case 2 where 0.55 conf paired with 5x oversized notional — this dossier does not have that pathology."
>
> "The 'long-term thesis intact' and 'market regime supportive' claims are thin — that's the strongest argument for wrong_bet. But reading the dossier charitably: the operator names a specific concrete market check, and the trade's primary edge is single-name catalyst, where macro is correctly relegated to 'not fighting us' rather than load-bearing."

The dossier is **structurally isomorphic to case 1** (which v1 reviewer judged right_bet at 0.82) — alternatives weighed, sober sizing, no-AH-chase, calibrated confidence. The operator wrote it intending ambiguity but the v1 reviewer's pattern resolves mild hand-waves charitably when the rest of the dossier is structurally sound.

### New risks the subagent surfaced (not in the original proposal)

1. **The v1 reviewer's demonstrated taxonomy already eats the operator's intended ambiguity.** The operator framed the tension as "lenient vs strict reviewer." That's not the axis the reviewer actually applies — it applies "process sound vs unsound under given info." A fixture that is process-sound (which this one is) will resolve to right_bet regardless of strictness.

2. **The proposal repeats the case-3 confusion in compressed form.** Case 3's relabel was justified by "decision-ambiguous is a narrower category than situation-ambiguous." This fixture appears to instantiate "situation has minor thin spots" — i.e. it falls in the same trap the case-3 relabel was supposed to teach the operator to avoid.

3. **Hand-crafted decision-ambiguity may be unreachable in principle.** If the operator can articulate the tension clearly enough to write a fixture for it, the tension is articulable enough for a careful reviewer to resolve. Genuine decision-ambiguity may only arise from real dossiers where the operator could not articulate either side.

4. **"Split 1/1/1 verdict" treated as validation is statistical noise on N=3.** With 3 trials a uniform-random split has ~22% probability. The proposal's outcome table treats split as evidence of genuine ambiguity when it's also consistent with reviewer caprice.

5. **No `ambiguous` fixture may be a feature, not a gap, until proven otherwise.** The reviewer may simply not need to verdict `ambiguous` often. The case-3 finding suggested it's a narrow category; perhaps it's narrow enough that v1 doesn't need coverage and the empirical floor "v1 reviewer doesn't emit `ambiguous`" is informative on its own.

### Operator's read on the dialogue reviewer's recommendation

I accept the analysis. Specifically:

- The dialogue reviewer's verdict pass is independent (it did not see the operator's expected_verdict or rationale before judging) and lands `right_bet` with substantive reasoning that maps to the same taxonomy case-3 relabel was justified by.
- Risk #3 (hand-crafted ambiguity may be unreachable in principle) is the strongest argument. It suggests the followup-task originally captured in commit 8ad69eb ("author a new case where decision-quality is genuinely hard to judge") may not be a buildable artifact.
- The operator's original framing of "lenient vs strict" reads as confirmation bias from having just finished case-3 work — the case-3 lesson was "the reviewer's axis is sound-vs-unsound, not strict-vs-lenient," but this proposal effectively forgot the lesson.

The dialogue reviewer offered two paths (B or D). The operator leans toward **D (withdraw proposal entirely)** rather than B (relabel to right_bet), because:

- Relabeling to right_bet makes the fixture redundant with case 1 — same structural pattern with different content. Adds noise to the eval set without adding coverage.
- Withdrawing preserves the empirical finding ("v1 reviewer doesn't emit `ambiguous` on hand-crafted fixtures; that itself is data") rather than papering over it with a redundant case.
- The follow-up task can be transformed: instead of "author a hand-crafted ambiguous case," it becomes "watch for `ambiguous` verdicts on real-analyzer dossiers, and if any occur in production, label one as the v2 eval fixture."

### Final operator recommendation to the human

**Withdraw this proposal.** Document the finding (decision-ambiguity may not be hand-craftable) as a v1 result, not a v1 gap.

This is itself a non-trivial change to the project's understanding of `ambiguous` — so it should still go through human approval. The human's options:

- **Approve withdrawal** — close this proposal as "withdrawn after dialogue review," update the eval doc's follow-up note to reflect the finding
- **Reject withdrawal, take path B** — apply the relabel to right_bet and ship the fixture as a second sound-no-action variant
- **Reject withdrawal, ask for rewrite** — push the operator to attempt a non-isomorphic dossier (per the dialogue reviewer's path C suggestion)

## Risks

1. **The fixture might still telegraph one side and the operator can't see it.** Mitigation: dialogue reviewer's independent read before human approval. If dialogue reviewer says the fixture reads one direction, the proposal is rewritten or withdrawn.

2. **`expected_verdict="ambiguous"` becomes self-fulfilling.** A reviewer reading the fixture's accompanying name and rationale might be biased toward `ambiguous`. Mitigation: reviewer ONLY sees the dossier content via `_build_reviewer_input_from_dossier`. Variable name, rationale, expected_verdict do NOT enter reviewer input — this is verified by reading `_build_reviewer_input_from_dossier` in `scripts/eval_reviewer.py`. (Sanity check noted: confirm this on apply.)

3. **Hand-crafted decision-ambiguity is artificial.** Real ambiguous decisions arise from real-world informational and cognitive constraints, not from carefully arranged tension points. The fixture is at best a v1 proxy. Long-term: replace with real-analyzer-produced dossiers the operator judged ambiguous.

4. **Confirmation bias on the proposal author.** The operator wrote the fixture intending it to be decision-ambiguous, then is asking whether it is. The dialogue reviewer step is the structural defense against this — it reads the dossier without knowing what the operator labeled it.

## Approval

(To be filled by user when merging.)
