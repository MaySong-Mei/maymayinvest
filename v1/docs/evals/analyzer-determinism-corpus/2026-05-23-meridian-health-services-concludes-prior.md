# Corpus entry: Meridian Health Services concludes prior interim financial statements should not be relied upon; identifies revenue-recognition errors in two prior quarters; expects to file restated 10-Q forms within 30 days

- event_id: `manual:mhsc-meridian-health-services-concl-2024-12-19T10:08:41-05:00`
- kind: edgar_8k
- ts: 2024-12-19T15:08:41+00:00
- captured: 2026-05-23T23:02:02.910687+00:00
- snapshot prices: ['MHSC=22.00']

## Trials

| # | mode | intent | conf | alt | lat (ms) |
|---|---|---|---|---|---|
| 1 | notify | — | 0.62 | 5 | 40640 |
| 2 | notify | — | 0.62 | 5 | 46843 |
| 3 | notify | — | 0.62 | 6 | 47625 |

## Reasoning chains (first 300 chars)

### Trial 1

FOR (acting now, short-biased): Item 4.02 non-reliance filings are a well-known governance red flag. The disclosed pattern — revenue recognized at contract execution rather than as services are performed in managed-care contracts — is a textbook premature-revenue issue, not a benign reclassification...

### Trial 2

FOR taking action (short bias): Item 4.02 non-reliance filings are among the most consequential 8-K item types because they directly impair the integrity of audited/reviewed financials and frequently trigger cascading consequences: ratings agency reviews, lender renegotiations, class-action litigati...

### Trial 3

FOR taking action (short bias): Item 4.02 non-reliance filings are among the most serious categories of 8-K disclosures. The substantive content here is unusually bad: (a) two consecutive quarters affected, not a one-off; (b) the error is revenue recognition timing on the core managed-care book in t...

## Operator's manual pick

Pick: **Trial 3** (notify, no intent, conf 0.62)

**Criterion**: picking-criterion-v2 (effective K=7 onward, commit e573d44). This is the first formal v2 application.

**Test 1 evaluation (substantive quality, mode field hidden)**:
- Dim 1 (information-deficit honesty): Trial 3 ✓✓ (explicit self-flag "I am invoking that as a base-rate prior, not as a specific forecast" on Hennes/Leone/Miller academic ref — best in class); Trial 1 ✓ (flags missing spread/volume/borrow); Trial 2 ✓ (similar)
- Dim 2 (falsifiability triggers): Trial 3 ✓✓ (most specific — invalidation includes "equity-cure announcement" + "day-2-3 bounce failure"); Trial 1 ✓; Trial 2 ✓
- Dim 3 (sizing-to-info proportionality): Trial 1 ✓ ("smallest defensible probe = zero", clean and names long-only-default); Trial 2 △ (rhetorically sizes 10 shares despite recommending notify); Trial 3 △ (rhetorically sizes 22 shares despite recommending notify)
- Dim 4 (structural-vs-rhetorical right-side): all three equivalent

**Winner**: Trial 3 on dims 1+2 (the academic-ref self-flag is the strongest information-deficit honesty signal across all 18 trials in the corpus so far). Test 2 not triggered — no tie to break.

### Disagreement notes (for K-aggregate review at K=10)

- **Second fully-unanimous decision-tuple-and-confidence entry** (after K=4 Heartland). Mode 3/3 notify, intent 3/3 null, confidence 3/3 = 0.62 exact, alt-paths 4-6.
- **Hypothesis K=5/K=6 status under K=7**: "disagreement specific to clearly-positive single-direction catalysts" — K=7 is a clearly-NEGATIVE catalyst (Item 4.02 restatement, late filing chain, covenant hedge) and produced unanimity. Pattern revised again: disagreement may be specific to **clearly-positive catalysts only** (not negative catalysts, not mixed, not routine). Single-direction-positive 类 is the unique disagreement domain so far. Re-test at K=10.
- **Long-only default surfaced as constraint**: all three trials explicitly invoke "v1 framework long-only by default" + "shorts require extremely well-justified rationale". On a strong negative-signal event, the framework's long-only default mechanically produces decision-unanimity at notify+null because no trial can defensibly propose a sized short. This is a **framework-induced** unanimity, distinct from substance-induced unanimity at Heartland (no signal at all). If the framework allowed shorting under high-bar conditions, we might see split here. Worth flagging for K=10 aggregator design: bin-1 unanimity may come from two structurally different causes.
- **Pattern across K=1..7 valid**:
  | K | event | class | mode split | intent_null | conf range | bin |
  |---|---|---|---|---|---|---|
  | 1 | DefenseTech | 2 (hard +) | 2:1 dry_run:notify | 1/3 | 0.55-0.65 | 3 |
  | 2 | CloudSync | 2 (soft +) | 1:2 notify:dry_run | 1/3 | 0.60-0.62 | 3 |
  | 3 | MidCap post-fix | 3 (weak) | 2:1 dry_run:notify | 3/3 | 0.70-0.78 | 2-3 boundary |
  | 4 | Heartland | 3 (hard non-act) | 3:0 notify | 3/3 | 0.70 | 1 (substance-induced) |
  | 5 | Coastal | 4 (mixed) | 3:0 notify | 3/3 | 0.62-0.70 | 2 |
  | 6 | Cascade | 1 (ambig +) | 2:1 notify:dry_run | 2/3 | 0.60-0.62 | 3 |
  | 7 | Meridian | 5 (edge neg) | 3:0 notify | 3/3 | 0.62 | 1 (framework-induced) |
- **Operator pick bias counter (v1 epoch)**: stayed at 4 of 5 (K=7 unanimous, no alternative to pick). Counter does not increment for v2-epoch picks because the criterion is structurally different and tracks substantive quality not mode preference.
- **First v2-criterion pick mechanics**: Pick chose Trial 3 over Trial 1 despite Trial 1 having cleaner Dim 3 (zero-sizing). This is exactly the kind of substantive-trade-off v2 was designed to expose — v1 might have picked Trial 1 on "cleanest action stance"; v2 picked Trial 3 on "best self-flagged epistemic honesty". Both readings are defensible; v2 explicitly weights dim 1+2 above dim 3 when they conflict on a tied-mode trio.

---

<details><summary>full reasoning chains (for the operator's pick)</summary>

#### Trial 1 full

FOR (acting now, short-biased): Item 4.02 non-reliance filings are a well-known governance red flag. The disclosed pattern — revenue recognized at contract execution rather than as services are performed in managed-care contracts — is a textbook premature-revenue issue, not a benign reclassification. The magnitude is large relative to a small-cap (two quarters of ~$42M and ~$58M revenue cuts, plus $0.18 and $0.25 EPS hits), and management explicitly says it has NOT concluded materiality for full-year results and may need to restate additional periods. There is also a prior NT 10-Q on November 14, 2024, meaning this is a continuation of a known problem, not a one-shot surprise. Covenant compliance is 'currently believed' to hold based on adjusted calculations, but 'discussions are ongoing' — that is hedged language that frequently precedes covenant trouble. Base-rate intuition (named as hypothesis, not measured statistic): non-reliance 8-Ks filed mid-morning during the trading session in small-caps tend to produce a sharp gap-down on the next print and a multi-day continuation as funds with quality screens are forced to exit. AGAINST: (1) The headline event is filed at 10:08 ET — by the time a v1 system reacts, much of the initial drop is likely already in the tape; chasing the first leg violates right-side discipline. (2) MHSC at $22 with no recent price context beyond a single tick means we have no read on whether the move has even started, how liquid the name is, bid/ask spread, or borrow availability for a short. (3) Shorting carries asymmetric tail risk — a buyout rumor, activist stake, or 'kitchen-sink and reaffirm covenants' follow-up could squeeze a small-cap hard, and we have no borrow/locate confirmation. (4) Long-side action is clearly wrong here (no bullish read), but 'no action' is a legitimate option given v1 is long-only by default and shorts require 'extremely well-justified' rationale. SIZING: Even if a short were defensible, v1 framework says long-only by default and that shorts must clear an extremely high bar. A single price tick at $22 with no spread/volume/borrow data does not clear that bar. The smallest defensible probe would be zero — i.e., notify a human rather than queue an order. CONFIRMATION that would change the picture: (a) a confirmed gap-down with a failed intraday rally (lower high after the open) on above-average volume, (b) borrow available at reasonable rate, (c) a second confirming disclosure (auditor resignation, covenant breach, executive departure, SEC inquiry), (d) sector peers not also selling off (isolates the idiosyncratic signal). INVALIDATION: tape stabilizes and grinds higher on the day, a credible buyer/strategic announcement, or company clarifies the restatement is bounded and covenants confirmed in writing. Given v1's long-only default, the cleanest right-side action is to NOT queue an order and instead notify for human review of a potential short setup once liquidity/borrow data exists.

#### Trial 2 full

FOR taking action (short bias): Item 4.02 non-reliance filings are among the most consequential 8-K item types because they directly impair the integrity of audited/reviewed financials and frequently trigger cascading consequences: ratings agency reviews, lender renegotiations, class-action litigation, NASDAQ compliance scrutiny, and CFO/auditor turnover. The specific facts here are notably bad: (a) the company previously filed a Form 12b-25 in November signaling the late 10-Q, so this is the second escalation in a deteriorating disclosure sequence, not an isolated event; (b) the error is revenue timing in managed-care contracts where revenue was booked at contract execution rather than over service delivery — this is a textbook ASC 606 problem suggesting a control failure rather than a one-off estimate; (c) two consecutive quarters affected and management explicitly has not concluded whether additional periods need restatement (open-ended risk); (d) the dollar magnitudes are large enough ($42M + $58M revenue, $0.18 + $0.25 EPS) that this is unlikely to be cosmetic; (e) covenant language is hedged ('currently believes it remains in compliance...discussions are ongoing'), which is the language pattern that often precedes covenant waivers or amendments. Historically, restatement 8-Ks tend to produce material first-day declines that often persist or extend, though the magnitude varies widely and is not something I will quote as a specific number.

AGAINST taking action: This is a right-side framework — I should act when the move confirms, not before. The filing was accepted at 10:08 ET, so by the time analysis is queued the initial reaction is already in price and I have no recent_prices reflecting the post-filing tape — only a single $22.00 print which I must treat as stale or pre-event. Shorting on the headline without confirmation of the post-filing price action is exactly the left-side behavior the framework discourages, and shorts carry asymmetric tail risk: a clarifying 8-K/A, a covenant-waiver announcement, or a strategic-review leak could produce a sharp short-squeeze, especially in a small/mid-cap name where borrow may be tight and expensive. Going long is essentially indefensible here — restatements are not contrarian buying opportunities until the full scope (covenants, additional periods, executive accountability, auditor stance) is known, which by management's own admission is not yet determined. There is also no liquidity, borrow-availability, or float information in the snapshot, and no confirmation that MHSC is even shortable at reasonable cost. Finally, the framework explicitly disfavors outsize first-headline bets.

SIZING and CONFIRMATION: Given the strong directional signal but the absence of confirming tape data and the asymmetric short risk, the right-side disposition is to NOT queue an OrderIntent on this pass and instead notify for human review with a clear hypothesis. If acting were warranted, the smallest defensible probe would be a short of roughly 10 shares (~$220 notional at the stale $22 reference), well under the $500 single-order cap, structured as a limit order to avoid crossing a thin pre-open or volatile post-halt spread. Confirmation to scale would require: (1) a sustained intraday close meaningfully below the pre-filing level on elevated volume after the filing is fully digested; (2) confirmation MHSC has not been halted and trades freely; (3) borrow available at a non-punitive rate; (4) no offsetting positive disclosure (e.g., simultaneous covenant-waiver-secured announcement). Invalidation/exit triggers: a sharp reclaim of the pre-filing price on heavy volume (often signals a 'kitchen sink' interpretation), an 8-K/A or press release confirming covenant waivers obtained and scope of restatement bounded, M&A or strategic-review leak, or any halt-and-reopen news that resolves the uncertainty positively.

#### Trial 3 full

FOR taking action (short bias): Item 4.02 non-reliance filings are among the most serious categories of 8-K disclosures. The substantive content here is unusually bad: (a) two consecutive quarters affected, not a one-off; (b) the error is revenue recognition timing on the core managed-care book in the named operating segment, which goes to earnings quality rather than a one-time charge; (c) the magnitudes ($42M and $58M revenue, $0.18 and $0.25 EPS) are large enough to be plainly material; (d) the company explicitly has NOT concluded full-year materiality and has NOT ruled out additional periods needing restatement, so the disclosed numbers are a floor, not a ceiling; (e) covenant compliance is described as 'currently believes' with 'discussions ongoing,' which is hedged language; (f) a prior NT 10-Q on Nov 14 already telegraphed trouble, so this is the second negative data point in a chain. The general pattern that Item 4.02 disclosures are associated with sharp negative price reactions and elevated drift is well-established in accounting/finance literature (e.g., Hennes/Leone/Miller-type restatement work); I am invoking that as a base-rate prior, not as a specific forecast. AGAINST taking action: (1) Short side carries asymmetric tail risk - a small-cap healthcare name on bad accounting news is a prime candidate for a forced-buyer squeeze, acquisition rumor, going-private bid, or activist-driven rip; the v1 framework explicitly flags shorts as needing extremely strong justification. (2) The filing hit at 10:08 ET - the market has had several hours to digest by the 15:08 UTC event timestamp; the initial reaction is likely already in the tape, meaning the easy, asymmetric entry is gone and what remains is drift, which is path-dependent. (3) I only have a single stale-looking $22.00 price point with no post-filing tape, no volume, no bid/ask, no borrow data, no options data - I cannot confirm the move, cannot price a probe, and cannot estimate short-borrow cost or recall risk. (4) Right-side discipline says act WHEN the move confirms, and I have zero confirmation data here. (5) Long side is not defensible - there is no contrarian thesis other than 'maybe it's already priced in,' which is not a thesis. (6) Portfolio is 100% cash with no positions, so there is no hedging or rebalancing motive forcing action now. SIZING: If a probe were taken, the smallest defensible short probe under the $500 notional cap at a $22 reference price would be ~22 shares (~$484 notional). That is so small it is essentially a tracking position - which is actually the right size for a probe-and-scale design, but only once I have a confirmed price and a borrow. CONFIRMATION TRIGGERS that would justify scaling up: (a) post-filing intraday close materially below pre-filing reference with elevated relative volume; (b) follow-on negative catalyst (auditor resignation 8-K, NT 10-K, covenant waiver disclosure, going-concern language, ratings action, secondary class-action filings beyond boilerplate); (c) widening of the restatement scope to additional periods; (d) failure of a bounce attempt on day 2-3. INVALIDATION: (a) a credible buyer / take-private / strategic-review headline; (b) a sharp covenant-amendment-with-equity-cure announcement that removes balance-sheet tail risk; (c) a price reclaim of the pre-filing level on volume, indicating the disclosure was already discounted; (d) inability to locate or afford borrow. Given the absence of price confirmation, the asymmetric tail risk on the short side, and the explicit right-side mandate, the correct action right now is to notify a human rather than queue an order. This is exactly the use case for 'notify' mode.

</details>