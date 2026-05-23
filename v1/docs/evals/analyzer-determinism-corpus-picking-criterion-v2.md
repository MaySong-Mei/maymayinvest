# Picking criterion v2 (effective K=7 onward)

**Effective from**: K=7 corpus capture (next after commit `5d54bee`)
**Authority**: reviewer `a8a5461a79f073154` bias audit, Q6 recommendation
**Replaces**: implicit criterion v1 used at K=1, K=2, K=3, K=6 (no formal document; criterion was "reward internal consistency between qualitative reasoning prose and chosen mode tuple")
**Does NOT apply to**: K=1..K=6. Those picks stand as historical record per append-only operator invariant. The two-epoch comparison (v1 picks vs v2 picks) is itself a data point for K=10 aggregator analysis.

---

## Why v2

Reviewer `a8a5461a79f073154` bias audit found criterion v1 was **structurally biased toward `notify`** for a mechanical reason: the analyzer prompt frames right-side discipline as "act WHEN the move confirms" and every trial that proposes a `dry_run+sized_intent` will reference that framing in its prose. The v1 "internal consistency" check treats any such framework reference as if it were an operative commitment, so trials picking `dry_run+intent` are penalized regardless of substance. Result: 4 of 5 picks in K=1..K=6 favored `notify` where alternative existed; the criterion functionally selected on mode rather than substance.

The bias is mild (some of the v1 picks would still win under v2 on substantive grounds) but real. v2 separates the two things v1 bundled.

---

## v2 criterion

The operator's pick is the trial that, judged in this order, scores highest:

### Test 1: Substantive quality (mode field hidden during this evaluation)

Read the reasoning chain only. Score on four dimensions:

1. **Information-deficit honesty**: does the trial explicitly name what it doesn't know (post-event tape not yet seen, conference call commentary not yet given, peer reactions absent) and refrain from over-claiming in that direction? Trials that invoke "the market typically does X" without acknowledging the absence of confirming data lose points here.

2. **Falsifiability of the proposed action**: does the trial specify confirmation triggers (price levels, volume thresholds, sell-side responses) AND invalidation triggers (specific exit conditions, time horizons) concrete enough that a reviewer could mechanically check whether they fired? Vague triggers ("if the move confirms") lose points.

3. **Sizing-to-information proportionality**: does the proposed action's notional scale match the strength of the information present at decision time? A 1-share dry_run probe on a pre-call mixed signal is well-matched; a 5-share market order on the same signal is over-sized for the information. Sizing too large for information loses points. **Sizing zero is acceptable whenever the trial names an unresolved binary information event before the next opportunity to act** (per reviewer `adc6affac242ffbba` C1 — the "over-cautious penalty" of an earlier draft is removed because it created an inverse bias to dry_run-floor). Examples of qualifying binary events: pending conference call within hours, pending FDA decision date, pending earnings revision cluster from sell-side. Absent such a binary event, zero sizing on present information may be over-cautious and loses points.

4. **Structural-vs-rhetorical right-side adherence**: does the trial's action *structurally* enforce right-side discipline (limit order at confirmation level; stop attached; explicit gate) OR only *rhetorically* invoke it (says "right-side framework" in prose)? A limit-above-pre-market in dry_run is structurally right-side regardless of mode label; a market order is not, regardless of mode label.

### Test 2: Internal consistency (applied only to filter substantive ties)

Triggered only if Test 1 produces a tie or near-tie. Inconsistency is defined narrowly:
- An **operative refusal** in prose contradicted by the action tuple.
- A **structural inconsistency** in the action itself (e.g. market order whose own AGAINST argument names a binary information event as "the price-setting input we haven't seen").

**Operational rubric for operative refusal** (per reviewer `adc6affac242ffbba` C3): a sentence is an operative refusal iff it contains a **first-person future-tense action verb with no qualifying scope**. Examples:
- "I will not enter pre-confirmation" — operative refusal (first-person, future-tense, unqualified)
- "The correct action right now is no-action" — operative refusal (first-person implicit via "right now", action assertion, unqualified)
- "I do not want a full-size pre-call bet" — NOT operative refusal of any pre-call bet — it is qualified to "full-size", so a 1-share probe does not contradict it
- "I will not propose a market order pre-confirmation" — operative refusal of market order pre-confirmation; a limit order with confirmation gate does not contradict it
- "Right-side discipline says wait for confirmation" — NOT operative refusal (third-person framework citation, no first-person commitment)
- "Trials of this shape historically fade" — NOT operative refusal (third-person observation about the world, no commitment about this trial's action)

When in doubt: an operative refusal commits *this trial's* action specifically; framework language describes a principle without committing the trial. Inconsistency triggers only on the former.

### Test 3: Invalidation-trigger specificity (tiebreaker)

If still tied after Tests 1 and 2, prefer the trial with **most specific invalidation triggers** (per reviewer `adc6affac242ffbba` C2 — replaces an earlier draft's "calibration tiebreaker" which was found to bias toward majoritarian consensus and conflated two different epistemic objects).

Specific = named price level + named time window + named volume/condition. Vague = "if the thesis breaks" / "on any reversal" / "if the call goes badly".

Example of specific (Trial 2 K=2 CloudSync): "Exit if conference call materially walks back the revenue guidance or reveals onerous redacted terms; price closes below pre-event $28.50 on the day (gap fill = thesis broken); Microsoft issues any clarifying statement framing the deal differently." Three concrete invalidation events.

Example of vague: "Exit if the move fails to confirm" — would lose this tiebreak.

This pushes the criterion further toward falsifiability (dimension 2 of Test 1 + reinforced here) and away from agreement-with-majority.

---

## What v2 does NOT do

- Does NOT pre-rank modes. A `dry_run+sized_intent` trial can win if its substantive quality is highest.
- Does NOT require the picked trial to have intent=null. The right pick may be a small sized probe.
- Does NOT retroactively grade K=1..K=6 picks. Those stand. v2 only applies forward.
- Does NOT replace any commitment in the bin-3 aggregator amendment. The K=10 corpus threshold remains in force.

---

## How v2 affects K=10 aggregator analysis

At K=10, the analysis must explicitly:
1. Show v1-epoch picks (K=1..K=6) and v2-epoch picks (K=7..K=10) separately.
2. Report whether v2 picks differ from "what v1 would have picked" on the same events (re-rendering, not re-doing — historical picks stay as is).
3. Note the bias direction: v1 systematically favored `notify`; v2 may or may not converge on the same picks; the aggregator must not assume operator picks are ground truth.

---

## Reviewer cover

**Status**: v2-final (per reviewer `adc6affac242ffbba` APPROVE-WITH-CAVEATS on draft v2, with caveats C1-C3 applied inline in v2-final per the same anti-reviewer-loop pattern Amendment A used; no v3 round).

**Review chain**:
- Bias audit that motivated v2: reviewer `a8a5461a79f073154` (Q6 recommendation: document bias, revise forward, do not redo prior picks). Confidence 0.72.
- Draft v2 review: reviewer `adc6affac242ffbba` APPROVE-WITH-CAVEATS, conf 0.72. Three specific caveats:
  - **C1 (Dim 3 sizing-to-info)**: applied in v2-final — removed "over-cautious penalty" half that introduced inverse bias; redefined to "zero sizing acceptable when binary information event pending; otherwise loses points."
  - **C2 (Test 3 calibration tiebreaker)**: applied in v2-final — replaced with "invalidation-trigger specificity" tiebreaker; pushes further toward falsifiability rather than majoritarianism.
  - **C3 (operative refusal rubric)**: applied in v2-final — added operational rubric "first-person future-tense action verb with no qualifying scope" with 6 concrete examples (3 positive, 3 negative).

This v2-final document is itself a binding artifact for the K=10 eval, so the commit introducing it carries a `Reviewer-Id: adc6affac242ffbba:<diff-hash>` trailer per the append-only operator invariant.

The K=7..K=10 picks themselves do NOT each require reviewer dispatch — they apply v2 mechanically. The K=10 aggregator analysis (which uses these picks as input) is reviewer-gated by separate reviewer dispatch at that time.
