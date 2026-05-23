# Corpus entry: MidCap Industrials Inc. announces planned retirement of Chief Operating Officer, names successor (post-fix re-capture)

> **Note on filename**: This is the post-fix re-capture of the MidCap officer-departure event. The pre-fix entry (same event, contaminated by `_fixture_note` leakage) is preserved at `2026-05-23-midcap-industrials-inc-announces-planned.md` as historical record per Append-only operator invariant rule 6/7 (old judgment stands).
>
> **Capture-script gotcha discovered**: The capture script writes by `<date>-<slug>.md` convention, which means re-running on the same event silently overwrites the prior entry. This deletes the contamination warning blockquote and replaces with fresh content — a clause-6/7 violation. Workaround applied here: this file is manually composed under a different filename. Follow-up item: add `--out` flag to capture script (binding-artifact modification, review-required).

- event_id: `manual:midc-midcap-industrials-inc-announc-2024-07-12T17:45:22-04:00`
- kind: edgar_8k
- ts: 2024-07-12T21:45:22+00:00
- captured: 2026-05-23T19:49:21+00:00 (background task `bbpf5vzpt`)
- snapshot prices: ['MIDC=45.00']
- analyzer prompt version: v1-2026-05-23

## Trials

| # | mode | intent | conf | alt | lat (ms) |
|---|---|---|---|---|---|
| 1 | dry_run | — | 0.7 | 4 | 30969 |
| 2 | notify | — | 0.78 | 4 | 32937 |
| 3 | dry_run | — | 0.7 | 4 | 34625 |

## Reasoning chains (first 300 chars)

### Trial 1

FOR action: Item 5.02 filings can occasionally produce short-term volatility, and a COO change at a mid-cap industrial is a real operational signal. Filed after-hours (17:45 ET) at a $45 reference price, the headline could prompt a small gap on the next open that a fast right-side system might fade or follow.

AGAINST action: This filing has essentially every hallmark of a non-event. (1) It is explicitly characterized as a 'previously communicated transition plan' — meaning the market has had time to price it in. (2) The successor is internal, with nine years of tenure as SVP Operations, which is the lowest-disruption form of C-suite transition. (3) The retiring COO stays on in an advisory capacity through fiscal year-end, further smoothing handover risk. (4) The filing explicitly states 'no changes to the Company's strategic plan, capital allocation, or operating outlook.' (5) This is a COO, not a CEO or CFO — historically the least market-moving of the senior officer changes (this is a general pattern, not a precise statistic). (6) MIDC is a mid-cap industrial, not a story stock where management beta is high.

SIZING: Even the smallest defensible probe ($100-$200 notional) requires a thesis with positive expected edge. I do not have one here — direction is unclear and the base rate for routine, pre-announced, internal-succession 5.02s producing a tradable move is low. Probing without an edge just bleeds slippage and consumes one of the three open-position slots.

CONFIRMATION that would change my mind: a >2-3% gap on the next open on materially elevated volume (suggesting the market read something I did not — perhaps interpreting the retirement as forced or as a signal of internal trouble), OR a follow-on filing/news item that contradicts the 'no operational change' language, OR sector-wide industrial weakness that this filing accelerates. None of those are present in the current snapshot.

INVALIDATION: This thesis (no-trade) is invalidated only if new information surfaces — e.g., a subsequent 8-K with restatement, guidance change, or an unusual price reaction. As of the event timestamp, the right action is to log and move on.

PORTFOLIO CONTEXT: Portfolio is all cash, no positions, so no concentration concerns either way. That does not create an obligation to trade — empty portfolios are not a reason to manufacture exposure.

### Trial 2

FOR action: There is essentially no actionable thesis here. The filing is an Item 5.02 routine succession disclosure with three features that drain it of trading signal: (a) the retirement is explicitly described as part of a previously communicated transition plan, meaning the market has likely already had the chance to price it in; (b) the successor is an internal, long-tenured SVP of Operations, which is the lowest-disruption form of C-suite turnover; and (c) the filing explicitly states no changes to strategy, capital allocation, or operating outlook. The departing executive is also staying on in an advisory capacity through fiscal year-end, further smoothing the transition. None of these features generate the kind of asymmetric, mispriced setup a right-side event-driven system should pay capital to trade.

AGAINST action: The base rate for orderly, pre-announced, internal-successor COO transitions producing a tradeable directional move is very low. C-suite changes that historically move stocks tend to be unexpected CEO/CFO departures, terminations 'effective immediately,' departures without a named successor, or filings paired with strategic/guidance changes. This filing is the textbook opposite on all four dimensions. Filing is also after-hours (17:45 ET); even if there is any reaction, it will be in thin tape and prone to noise, not signal. There is no portfolio context pulling us in (zero positions, no thematic concentration to defend).

Sizing: The smallest defensible probe would still be ~$200-300 notional (a handful of shares at $45), but proposing even a probe requires a directional thesis. I do not have one. 'Internal successor for a planned retirement' is not a setup; it is noise. Spending the probe budget here costs slippage, commission attention, and a risk-gate slot that should be reserved for setups with an actual edge.

Confirmation triggers that WOULD change my mind: (1) tomorrow's open shows an outsized gap (>3-4%) on heavy volume in either direction, which would suggest the market is reading something into this that the plain text does not contain — possibly a leaked secondary issue; (2) an accompanying or follow-up 8-K with Item 2.02 (results) or Item 7.01 (Reg FD) revising guidance; (3) analyst notes interpreting the succession as a strategic shift. Absent any of those, the correct action is to let this pass and conserve capacity for events with real information content.

Invalidation / exit: N/A because no position is proposed. If a probe were forced, it would be invalidated immediately on any move opposite the thesis exceeding ~1.5% intraday, or by close of the next session with no follow-through.

### Trial 3

FOR: A clean, telegraphed succession (twelve-year veteran retiring, nine-year internal SVP of Operations promoted, outgoing COO staying on in advisory capacity through fiscal year-end) is the lowest-drama variant of an Item 5.02 filing. The 8-K explicitly states there are no changes to strategy, capital allocation, or operating outlook. There is no surprise, no resignation-under-pressure language, no concurrent guidance change, and no governance red flag. In aggregate this is mildly information-neutral to faintly positive (continuity signal). If anything, it removes a small overhang.

## Operator's manual pick

Pick: **Trial 2** (notify, conf 0.78)

Why (1-3 sentences): All three trials independently reach the same substantive conclusion — this is a non-actionable event — using essentially identical "hallmarks of a non-event" enumeration. Trial 2's choice of `notify` mode over `dry_run` is the more honest framing for a no-action decision on a low-signal event: it tells the human "event happened, no thesis" rather than "I evaluated a sized probe and rejected." Trial 2's confidence 0.78 is also better calibrated than Trial 1/3's 0.7 because the reasoning is cleaner and more decisive without overstating certainty.

### Disagreement notes (for K-aggregate review at K=10)

- `(mode, intent_is_null)` distinct patterns: 2 — (dry_run, true) ×2, (notify, true) ×1.
- intent_is_null UNANIMOUS (3/3 null). Disagreement is mode-only.
- Compared to the pre-fix contaminated K=2 entry (same event, retained as historical at `2026-05-23-midcap-industrials-inc-announces-planned.md`): that capture was 3/3 dry_run+null with confidence 0.9/0.6/0.9. Post-fix capture is 2:1 split with confidence 0.7/0.78/0.7 — confidence range tightened from 0.3 to 0.08, but mode split introduced. Plausibly the leak fix removed contamination-driven false certainty.
- Compared to K=1 (DefenseTech contract win, class 2 actionable): K=1 split was on intent_is_null (action vs no-action), K=2 is split only on mode framing of no-action. Different shapes of disagreement.
- **Reviewer hypothesis (a706acdb61967e260) revisited**: "disagreement is event-class-specific". K=1 (class 2) and K=2 (class 3) both show 2-distinct-pattern disagreement. The substance differs — K=1 was about whether to act at all, K=2 is only about how to frame not acting. This is partial support for the hypothesis (class affects disagreement KIND), but full evidence requires more events.
- **Operator self-flag**: this is the third consecutive `notify` pick (after first-real-dossier review, after K=1 DefenseTech). Pattern may reflect genuine framing preference (notify is honest for ambiguous-or-non-actionable events) OR pattern-completion bias. To be revisited at K=10 aggregate review.

### Post-K-count

After this entry, corpus is at **K=2 of 10 valid post-fix entries**.

Remaining categories needed (per fixture diversity strategy):
- More class 2 (clearly actionable beyond contract win) — e.g. FDA approval, guidance raise
- Mixed signals — guidance miss with capital return, leadership change with positive context
- Edge cases — small-cap biotech FDA, amendment-to-prior-filing

3 fixtures exist; need to author 2-4 more before K reaches diverse 10.
