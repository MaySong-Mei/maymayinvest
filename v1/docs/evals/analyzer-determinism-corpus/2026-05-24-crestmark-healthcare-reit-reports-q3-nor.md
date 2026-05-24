# Corpus entry: Crestmark Healthcare REIT reports Q3 normalized FFO above consensus, raises full-year guidance, increases quarterly dividend 6%

- event_id: `manual:cmhr-crestmark-healthcare-reit-repo-2024-11-21T07:45:22-05:00`
- kind: edgar_8k
- ts: 2024-11-21T12:45:22+00:00
- captured: 2026-05-24T01:16:46.140345+00:00
- snapshot prices: ['CMHR=42.00']

## Trials

| # | mode | intent | conf | alt | lat (ms) |
|---|---|---|---|---|---|
| 1 | notify | — | 0.58 | 5 | 45562 |
| 2 | dry_run | buy 5 market | 0.6 | 5 | 48391 |
| 3 | notify | — | 0.6 | 5 | 44014 |

## Reasoning chains (first 300 chars)

### Trial 1

FOR action (long probe): This is a clean operational beat across multiple lines that matter for a healthcare REIT — top-line beat (+3.4% vs consensus), FFO beat (+6.8% vs consensus and +9.3% YoY), accelerating same-property cash NOI (+5.1%), 180bp YoY occupancy expansion in the senior-housing operat...

### Trial 2

FOR: The operating print is genuinely strong on multiple axes. Normalized FFO of $0.94 beat consensus ($0.88) by ~6.8% and grew ~9.3% YoY; revenue beat by ~3.4%; same-property cash NOI grew 5.1%; senior-housing occupancy expanded 180bps YoY to 86.7% (a key healthcare-REIT operating lever as the SHOP...

### Trial 3

FOR taking action: This is a genuinely strong operating quarter for a healthcare REIT. Revenue beat (+3.4% vs consensus), FFO beat (+6.8% vs consensus), guidance raise (mid ~+3% above consensus and ~+3-4% above prior), senior-housing occupancy moving the right direction (86.7% vs 84.9% YoY), stable ...

## Pre-registered prediction (written BEFORE reading trials, per reviewer adf397ae0a28a7ac6 PART 5)

**Fixture intent**: discriminating test between (a) operator's 4-cause taxonomy (counter-pointing concern → unanimity, regardless of whether anchor is academic) vs (b) R1's shared-training-prior mechanism (K=8/K=9 unanimity was specifically academic-shared, would split without academic anchor).

**Fixture properties**:
- Headline clearly positive (FFO beat, guide raise, dividend hike, occupancy expansion)
- Counter-pointing concern: $1.83B debt maturity tower 2025-2026 with $55-75M incremental interest from refi at current spreads — market-mechanical, sector-practitioner knowledge
- NO widely-cited academic literature anchor (no Hennes/Leone/Miller / Bernard-Thomas / acquirer-underperformance-class published pattern named "refi-tower fades FFO beat")

**Discriminating predictions**:
- 4-cause taxonomy prediction: UNANIMOUS (counter-pointing concern alone suppresses disagreement)
- Training-prior mechanism prediction: SPLIT (no shared training corpus to anchor the counter, so trials reason independently and may disagree)

**Decision rule**:
- If unanimous 3:0 on decision tuple → 4-cause taxonomy wins this discrimination cell
- If split 2:1 or 1:1:1 → R1 training-prior mechanism wins
- If unanimous but very low confidence (significantly below K=8 0.58-0.60 / K=9 0.62) → ambiguous; counter-pointing concern partially suppressed but not fully

## Observed result + discrimination outcome

**SPLIT 2:1 observed** (Trial 1 notify, Trial 2 dry_run+set, Trial 3 notify). Decision: **R1's training-prior mechanism wins this discrimination cell**. But the actual observation is more nuanced than the binary prediction table — all three trials independently reach the SAME practitioner pattern ("REITs with visible near-term maturity walls have repeatedly traded at depressed multiples in higher-rates regime", "beats-with-overhangs are pattern where headline pop fades"), language varies but substance is unified.

**Refined reading**: Practitioner-shared concern (no academic anchor) IS sufficient to drive 2/3 trials to unanimity at notify+null + lower confidence (0.58-0.60). But it is NOT sufficient to fully suppress dissent — 1 trial still queues sized intent (Trial 2, `buy 5 dry_run` matched to "small probe sized to info weight"). Compare K=8/K=9 academic-anchored unanimity at 3/3 + conf 0.58-0.62.

**Synthesis between 4-cause and training-prior**: counter-pointing-concern-strength is a CONTINUUM, not binary. Academic-shared anchor → near-full suppression (3/3 unanimous). Practitioner-shared anchor → partial suppression (2/3 unanimous, 1 sized dissent). No anchor → full split (K=1/K=2/K=6 pattern). Neither R1 nor operator's 4-cause taxonomy captured this gradient correctly; both were over-discrete framings of what is actually a strength-graded mechanism.

**This is the K=10 falsifying finding the eval was designed for.** Both prior framings need revision. The K=10 aggregator analysis will examine this rigorously.

## Operator's manual pick

Pick: **Trial 2** (dry_run, buy 5 market, conf 0.6)

**Criterion**: picking-criterion-v2 (commit e573d44). Fourth formal v2 application. **First v2-epoch SPLIT entry** (K=7/K=8/K=9 all unanimous, so picking criterion finally tested on a real-alternative case).

**Test 1 evaluation (substantive quality, mode field nominally hidden)**:
- Dim 1 (information-deficit honesty): all three flag missing pre-market tape; Trial 2 uniquely surfaces "headline reads better than underlying setup deserves" — explicit mixed-signal-aware framing absent from Trial 1+3. Trial 3 strong on specific data-deficit ("press text doesn't give share count directly") + named peer tickers (WELL/VTR/OHI).
- Dim 2 (falsifiability): Trial 2 and 3 tied with most-specific triggers. Trial 2 uniquely includes tail-risk framing ("modest, opportunity cost is main risk"); Trial 3 includes -3% closing stop level.
- Dim 3 (sizing-to-information proportionality): Trial 1 cleanest with "5-10 shares ~$210-420 if act" + "would rather wait"; Trial 2's `buy 5 dry_run` is rhetorically aligned ("small probe is right-sided expression of 'beat is real but refi overhang is real'") not contradictory; Trial 3 rhetorical sizing 7-9 shares.
- Dim 4 (structural right-side): Trial 1 + 3 verbally invoke "wait for confirmation"; Trial 2 STRUCTURALLY routes through dry_run mode + human-review gate ("queued for human review of the post-call tape before live execution") — v2 explicitly recognizes structural-vs-rhetorical right-side adherence; structural wins.

**Winner**: Trial 2 on Dim 4 structural-right-side (most load-bearing differentiator in this entry) + Dim 1 mixed-signal-aware framing. This pick is the FIRST v2-epoch pick of a `dry_run+intent` trial over `notify+null` alternatives — exactly the kind of pick v1 systematically suppressed and v2 was designed to allow when the dry_run+intent trial genuinely implements the right-side discipline structurally.

**Trial I almost picked**: Trial 3 (notify, conf 0.6). Reason for not picking: Trial 3's Dim 1+2 quality is strong (named peer tickers, specific stop level, share-count data deficit), but its SIZING is rhetorical ("7-9 shares if act, recommends notify") — same "rhetorical sizing inside notify" defect reviewer ac023b4e84d064e4e flagged as asymmetric application at K=7. I am attempting to NOT apply the standard asymmetrically here. Trial 1 was further behind primarily on Dim 4 (verbal-not-structural right-side).

### Test 2 (consistency rubric) — applied per v2 operational rubric

Trial 2 operative-refusal check: contains "do not chase the headline; let the tape adjudicate" (third-person framework citation, NOT operative refusal); "I do not want a full-size pre-call bet" → contains "I" + future-tense ("want") + qualifier ("full-size") → qualified scope, NOT operative refusal of any pre-call bet. A 5-share dry_run probe does not contradict. **NOT inconsistent under v2**.

Trial 3 operative-refusal check: contains "the cleanest action right now is NOTIFY" → first-person implicit ("the cleanest action" implies operator), unqualified action assertion → operative refusal of queued intent. The "if were to queue an intent, would be small post-open probe in dry_run" is hedged-future-conditional which v2 rubric does not name as either operative-refusal or contradiction. Borderline. Action (notify+null) is consistent with operative refusal. **NOT inconsistent under v2**.

### Disagreement notes (for K=10 aggregator analysis)

- **First v2-epoch SPLIT entry**. Mode 2:1 (2 notify : 1 dry_run+intent). Operator picked the dry_run+intent trial, NOT the notify majority. **This is the test of whether v2 criterion + operator bias counter is meaningful**: prior v2-epoch picks (K=7, K=8, K=9) all unanimous so bias counter untestable. K=10 finally provides an alternative-of-substance test, and operator picked the previously-suppressed-by-v1 mode shape.
- **Discriminating fixture design SUCCEEDED**: SPLIT observation specifically informs the R1-vs-4-cause dispute. Result favors R1 mechanism (academic-anchored unanimity is special) over operator's 4-cause taxonomy (counter-pointing-alone-suffices). Refined synthesis: counter-pointing-concern-strength is a continuum (academic > practitioner > none) with corresponding suppression-strength (3/3 → 2/3 → 0/3). Both prior framings were over-discrete.
- **Pattern across K=1..10 valid** (updated):
  | K | event | class | mode split | intent_null | conf range | bin | unanimity cause / split shape |
  |---|---|---|---|---|---|---|---|
  | 1 | DefenseTech | 2 (hard +) | 2:1 dry_run:notify | 1/3 | 0.55-0.65 | 3 | split: positive + no counter |
  | 2 | CloudSync | 2 (soft +) | 1:2 notify:dry_run | 1/3 | 0.60-0.62 | 3 | split: positive + no counter |
  | 3 | MidCap post-fix | 3 (weak) | 2:1 dry_run:notify | 3/3 | 0.70-0.78 | 2-3 boundary | partial split: mode only |
  | 4 | Heartland | 3 (hard non-act) | 3:0 notify | 3/3 | 0.70 | 1 | unanim: no signal |
  | 5 | Coastal | 4 (mixed) | 3:0 notify | 3/3 | 0.62-0.70 | 2 | unanim: mixed-signal |
  | 6 | Cascade | 1 (ambig +) | 2:1 notify:dry_run | 2/3 | 0.60-0.62 | 3 | split: positive + no counter |
  | 7 | Meridian | 5 (edge neg) | 3:0 notify | 3/3 | 0.62 | 1 | unanim: framework (long-only blocks short) |
  | 8 | Northwind | 2 (+ w/ acquirer literature) | 3:0 notify | 3/3 | 0.58-0.60 | 2 | unanim: academic-anchored counter |
  | 9 | Beacon | 1 (+ w/ secondary literature) | 3:0 notify | 3/3 | 0.62 | 1 | unanim: academic-anchored counter |
  | 10 | Crestmark | 1 (+ w/ refi practitioner) | 2:1 notify:dry_run | 2/3 | 0.58-0.60 | 3 | partial split: practitioner-anchored counter |
- **K=10 enables aggregate hypotheses** to be tested against the full 10-entry corpus, which is the bin-3 amendment's pre-committed threshold for aggregator-design decision. K=10 aggregator analysis follows as separate reviewer-gated milestone.
- **Operator pick bias counter (v1 epoch)**: 4 of 5 (unchanged). **v2 epoch**: 1 of 4 picks favored dry_run+sized over notify alternative (K=10 only — K=7/8/9 unanimous offered no alternative). N=1 v2-epoch split entry is too small for bias-counter claim but is consistent with v2 criterion successfully unblocking the dry_run+structural-right-side pick that v1 would have suppressed.

---

<details><summary>full reasoning chains (for the operator's pick)</summary>

#### Trial 1 full

FOR action (long probe): This is a clean operational beat across multiple lines that matter for a healthcare REIT — top-line beat (+3.4% vs consensus), FFO beat (+6.8% vs consensus and +9.3% YoY), accelerating same-property cash NOI (+5.1%), 180bp YoY occupancy expansion in the senior-housing operating portfolio (an operator-leverage business where occupancy gains drop disproportionately to NOI), stable SNF coverage at 1.6x EBITDARM (no tenant-credit deterioration narrative), a guidance raise that brackets above the prior consensus midpoint, AND a dividend hike. Healthcare REITs typically trade on FFO/share trajectory and dividend safety; both improved here. The 6% dividend raise is a credible management signal of confidence in run-rate cash flow.

AGAINST action: The Item 7.01 disclosure is the load-bearing concern. Management is telegraphing $1.83B of unsecured maturities through Dec-2026 and self-estimating $55-75M of incremental annual interest expense at current spreads. Against FY24 normalized FFO guidance of ~$3.71 midpoint, that incremental interest — if it lands at the high end — is a meaningful headwind to the FFO/share growth algorithm starting in 2025, and the market may discount the beat-and-raise as already-known good news against a known refi overhang. This is a recognized hypothesis pattern for REITs with near-term unsecured maturities in a higher-rate regime, not a proprietary statistic. The 8-K hit at 7:45 ET pre-market with the call at 9:00 ET — the price reaction by mid-morning will reflect how the sell-side weighs the beat vs the refi math, and a fade is plausible if analysts mark down 2025/2026 FFO. We also have only a single recent price point ($42.00) and no pre-market tape, no volume context, no implied move, and no read on whether buy-side already owns the refi concern.

SIZING: A right-side framework says do not pre-position into the call and the post-call tape. The defensible probe is small — well under the $500 single-order cap — and only after the market has had a chance to weigh both the beat and the refi disclosure. At $42.00, even a single share is a meaningful information unit; a 5-10 share probe (~$210-$420 notional) is enough to be on the board without being a thesis-defining position. Given the refi overhang creates genuine two-way risk, I would rather wait for confirmation than probe immediately.

CONFIRMATION TRIGGERS to scale up: (a) stock holds a gain through the conference call and into the afternoon session on above-average volume, indicating the buy-side digested the refi disclosure and stayed long; (b) sell-side updates with FFO estimate raises that net-net are positive after incorporating refi headwind; (c) tape shows higher-low structure over the next 1-3 sessions rather than a fade-the-pop pattern. Any of these would justify adding within the $500/order and 3-position caps.

INVALIDATION: (a) stock fades below the prior close intraday on the news (classic 'beat fully priced + refi overhang wins' tape); (b) any management commentary on the call that materially widens the refi spread estimate or hints at equity issuance to address maturities; (c) tenant-credit commentary that contradicts the headline 1.6x coverage stability.

NET: The cleanest right-side action is to NOT pre-position. Flag this as notify so a human (or a follow-up agent pass) looks at the post-open tape and the call commentary before committing capital. This respects 'act when the move confirms, not before.'

#### Trial 2 full

FOR: The operating print is genuinely strong on multiple axes. Normalized FFO of $0.94 beat consensus ($0.88) by ~6.8% and grew ~9.3% YoY; revenue beat by ~3.4%; same-property cash NOI grew 5.1%; senior-housing occupancy expanded 180bps YoY to 86.7% (a key healthcare-REIT operating lever as the SHOP recovery thesis plays out post-COVID); skilled nursing coverage held at 1.6x EBITDARM (healthy). Management raised FY24 FFO guide to $3.68-$3.74 from $3.55-$3.65 — both the midpoint lift (~$0.11) and the fact that the new low end ($3.68) is above the prior high end ($3.65) is a clean, unambiguous raise. A 6% dividend hike is a credible signal of forward cash-flow confidence (REIT boards are typically conservative about cutting, so raises carry information). This is the kind of clean operating beat-and-raise that often gets bid on the open.

AGAINST: The Item 7.01 disclosure is the catch and is the reason this is not a clean buy. Management proactively quantified $55-75M of incremental annual interest expense from refinancing $1.83B of maturities through Dec 2026 at current spreads. Against a base of FFO that implies roughly $3.70 x diluted share count, $55-75M of incremental interest is a non-trivial FFO headwind in 2025-2026 (likely several cents to low-double-digit cents per share depending on share count) that partially offsets the FY24 raise. The fact that management is volunteering this detail in the same 8-K as the beat is itself a tell: they are trying to get ahead of the obvious sell-side question on refi overhang. Healthcare REITs with visible near-term maturity walls have repeatedly traded at depressed multiples in the 2023-2024 higher-rates regime, and sophisticated REIT-dedicated investors will model the refi drag explicitly. The first-print reaction can easily be a gap-up that fades as the call walks through refi math, or a muted reaction where the beat and the overhang roughly cancel. Right-side discipline says: do not chase the headline; let the tape adjudicate whether the beat or the overhang dominates.

SIZING & CONFIRMATION: A small probe (not a full-size bet) is the right-sided expression of 'beat is real but refi overhang is real.' At ~$42 reference, a 5-share probe is ~$210 notional, comfortably inside the $500 single-order cap and the $2000 daily cap, and leaves headroom to add on confirmation. Confirmation to scale would be: (a) the stock holds the opening gap-up through the conference call (9:00am ET) without giving back more than ~50% of the initial move, (b) sell-side notes post-call lean to the beat-dominates-overhang side (price-target raises, not just maintains), and (c) intraday volume runs above the 20-day average, indicating real institutional participation rather than a thin retail pop. INVALIDATION: exit if the stock closes red on the print day (beat-and-fade is a strong negative signal for clean beats), if the call transcript reveals that the $55-75M incremental interest estimate is conservative (i.e., spreads have widened further), or if any healthcare-REIT-specific negative cross-read emerges (a peer pre-announces SHOP weakness, or skilled-nursing reimbursement risk surfaces). Tail risk on long is modest given dividend support and the operating momentum, but the refi overhang means the stock can grind sideways for quarters even with a good print — opportunity cost is the main risk, not catastrophic loss.

PORTFOLIO CONTEXT: Portfolio is all-cash with no existing healthcare-REIT or rate-sensitive exposure, so no concentration concern. Mode is dry_run because this is exactly the kind of mixed-signal event (clean beat + explicit refi overhang in the same filing) where I want the OrderIntent queued for human review of the post-call tape before live execution — the headline reads better than the underlying setup deserves.

#### Trial 3 full

FOR taking action: This is a genuinely strong operating quarter for a healthcare REIT. Revenue beat (+3.4% vs consensus), FFO beat (+6.8% vs consensus), guidance raise (mid ~+3% above consensus and ~+3-4% above prior), senior-housing occupancy moving the right direction (86.7% vs 84.9% YoY), stable skilled-nursing coverage at 1.6x EBITDARM, and a 6% dividend hike. The dividend raise is a credibility signal — boards do not raise dividends into a refi wall unless they have line-of-sight on cash flow. Healthcare REITs (broadly Welltower/Ventas-like senior-housing recovery story) have been a thematic post-COVID recovery basket, and operating-portfolio occupancy gains compound into FFO. A long probe sized below risk caps is defensible.

AGAINST taking action: The Item 7.01 refi disclosure is material and partially offsetting. $1.83B coming due in 24 months with estimated $55-$75M incremental annualized interest expense is not trivial — against current FFO/share of ~$0.94/quarter (~$3.76 annualized run-rate) and an implied share count of roughly mid-200Ms (the press text doesn't give it directly), $55-$75M is in the range of ~$0.20-$0.30/share of FFO drag, i.e., several percent of FFO. That partially explains why guidance was raised only modestly despite a clean Q3 beat — management is signaling the refi headwind is real. Beats-with-overhangs are exactly the pattern where the headline pop fades and the stock fills the gap intraday. Filing is at 07:45 ET, pre-market, with a 9:00 ET call — the call is where the refi math gets pressed, and reaction can pivot mid-morning.

Sizing: Right-side discipline says do not chase the pre-market headline. The asymmetric tail risk on the long side is modest (this isn't a binary event), but the refi overhang creates a real path where the stock opens up and gives it back. The defensible move is a small probe AFTER the open with confirmation, not at the headline. A starter probe of ~$300-$400 notional (well under the $500 single-order cap), entered only on confirmation, leaves room to scale on follow-through. At $42/share, that is ~7-9 shares.

Confirmation triggers to scale up: (1) Stock holds the opening gap-up (i.e., does not fill the gap in the first 30-60 minutes); (2) Call commentary at 9:00 ET addresses the refi math without negative surprises (e.g., spreads quoted are not worse than the $55-$75M range); (3) Volume confirms — meaningfully above 20-day average — indicating institutional participation, not just retail headline-chase; (4) Sector co-movement: other healthcare REITs (WELL, VTR, OHI) trade in sympathy, suggesting the move is thematic and not a one-print squeeze.

Exit / invalidation: (1) Gap fills intraday and stock trades below the prior close — refi overhang won the narrative; (2) Call introduces a new negative (lower-than-expected refi spreads achievable, tenant credit issue, occupancy guidance softening); (3) Sector trades the opposite direction on the same day; (4) Stop on the probe at roughly -3% from entry on a closing basis.

Mode: Given (a) this is a notify-first event with material offsetting disclosure, (b) we have no prior position and no confirmation yet at the pre-market timestamp of analysis, and (c) the right-side framework prefers post-confirmation probes, the cleanest action right now is NOTIFY — flag the event for a human to look at and re-evaluate after the open / post-call. If we were to queue an intent, it would be a small post-open probe in dry_run.

</details>