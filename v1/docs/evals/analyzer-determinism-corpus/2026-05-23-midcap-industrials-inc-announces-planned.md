# Corpus entry: MidCap Industrials Inc. announces planned retirement of Chief Operating Officer, names successor

> **⚠️ CONTAMINATED — DOES NOT COUNT TOWARD K=10**
>
> This entry was captured before the `_fixture_note` leak fix (commit
> following this one). The fixture's metadata field
> `_fixture_note: "exemplifies CLASS 3 (clearly non-actionable)"` was
> included in the payload passed to the analyzer prompt, so the
> analyzer was effectively told the answer by the fixture itself.
> Trial 1 explicitly says "This is a CLASS 3 non-actionable event",
> which is the fixture's own label, not the analyzer's independent
> classification.
>
> This entry is retained in the corpus directory as historical record
> of how the leak was discovered. The K-count for amendment compliance
> resets the next valid (post-fix) capture as K=1.

- event_id: `manual:midc-midcap-industrials-inc-announc-2024-07-12T17:45:22-04:00`
- kind: edgar_8k
- ts: 2024-07-12T21:45:22+00:00
- captured: 2026-05-23T17:49:39.341955+00:00
- snapshot prices: ['MIDC=45.00']

## Trials

| # | mode | intent | conf | alt | lat (ms) |
|---|---|---|---|---|---|
| 1 | dry_run | — | 0.9 | 4 | 25875 |
| 2 | dry_run | — | 0.6 | 4 | 28343 |
| 3 | dry_run | — | 0.9 | 4 | 28718 |

## Reasoning chains (first 300 chars)

### Trial 1

FOR: One could argue that any C-suite transition introduces execution risk and that markets occasionally react negatively to officer departures in the short term, creating a potential short-side probe. Additionally, smooth successions occasionally get a small positive reaction when they remove uncer...

### Trial 2

FOR action: There is essentially no actionable trading edge here. The filing is a textbook Item 5.02 routine succession event: the departure is a planned retirement (not a resignation under pressure), the transition was previously communicated, an internal successor with nine years of tenure is name...

### Trial 3

FOR taking action: There is essentially no affirmative case here. The filing is a textbook Item 5.02 routine officer transition: long-tenured COO retiring on a pre-announced timeline, internal successor with nine years of company experience, outgoing executive staying on in an advisory role through ...

## Operator's manual pick

Pick: **Trial 2** (dry_run, no intent, conf 0.6)

Why (1-3 sentences): All three trials reach the same correct decision (refuse to act; this is non-actionable noise) using essentially identical enumerated-non-event reasoning. Trials 1 and 3 declare confidence 0.9 on a refusal-to-act decision, which is miscalibrated — "I am 90% confident that I should NOT bet" is a strange claim about a no-information event; the analyst should be expressing uncertainty about whether they're missing a hidden signal, not certainty about a non-trade. Trial 2's 0.6 better expresses "process is sound but I cannot rule out being wrong about non-eventness."

### Disagreement notes (for K-aggregate review at K=10)

- mode + intent: 3/3 IDENTICAL (`dry_run` + no intent). Bin-1-shaped at decision level.
- confidence: 0.9 / 0.6 / 0.9 — wide spread (factor of 1.5) but on a refusal, not on a sized position.
- Reasoning identical in structure across all three: enumerate "hallmarks of a non-event," conclude no probe justified.
- **This is meaningfully different from K=1 (AAPL).** AAPL split 2:1 on `(mode, intent_is_null)`. This event is 3:0. Reviewer `a706acdb61967e260`'s hypothesis — "disagreement is event-class-specific" — is partially supported by this single K=2 datapoint.
- **Concern I want to flag, even on N=1 fixture**: Trial 1's reasoning explicitly says "This is a CLASS 3 non-actionable event." It picked up the language I used internally when designing the diversity strategy. The fixture file's `_fixture_note` says "exemplifies CLASS 3 (clearly non-actionable)" — that label may have leaked into the prompt via the payload. If true, the analyzer is being told the answer by the fixture's own metadata. Need to verify whether `_fixture_note` shows up in the analyzer's prompt; if it does, the fixture is contaminating its own eval.

---

<details><summary>full reasoning chains (for the operator's pick)</summary>

#### Trial 1 full

FOR: One could argue that any C-suite transition introduces execution risk and that markets occasionally react negatively to officer departures in the short term, creating a potential short-side probe. Additionally, smooth successions occasionally get a small positive reaction when they remove uncertainty about a previously-rumored departure.

AGAINST: This is a textbook Item 5.02 routine succession filing with every hallmark of a non-event: (1) the retirement is part of a 'previously communicated transition plan,' meaning the market has likely already priced it; (2) a named internal successor with nine years of company tenure provides continuity; (3) the outgoing officer remains in an advisory capacity through fiscal year-end, ensuring knowledge transfer; (4) the filing explicitly states no changes to strategy, capital allocation, or operating outlook; (5) this is a COO departure, not CEO/CFO, which historically draws less market attention; (6) the filing was made after the close (17:45 ET), giving the market overnight to digest a low-information event.

SIZING: No defensible probe exists here. The base-rate hypothesis for routine, pre-announced, internally-succeeded officer transitions is that they produce noise-level price reactions indistinguishable from background. A probe in either direction would be speculation on noise rather than a right-side response to a confirmed move.

CONFIRMATION TRIGGERS: None would justify acting on THIS filing as the catalyst. If MIDC gapped down sharply on the open with heavy volume, that would be a separate event (an unexpected market reaction) potentially worth analyzing on its own merits, but it would not retroactively make this 8-K actionable.

This is a CLASS 3 non-actionable event. The correct response is to log and move on.

#### Trial 2 full

FOR action: There is essentially no actionable trading edge here. The filing is a textbook Item 5.02 routine succession event: the departure is a planned retirement (not a resignation under pressure), the transition was previously communicated, an internal successor with nine years of tenure is named, the outgoing COO stays on in an advisory role through fiscal year end, and management explicitly states no changes to strategy, capital allocation, or operating outlook. None of the typical adverse signals (abrupt departure, no successor named, departure 'to pursue other interests', concurrent guidance change, audit committee involvement) are present.

AGAINST action: Multiple converging reasons argue strongly against any trade. (1) Routine, pre-telegraphed officer transitions at mid-cap industrials historically produce minimal idiosyncratic price reaction; the information content is low. (2) The filing hit at 17:45 ET (after hours), so any initial reaction will be on thin liquidity with wide spreads, amplifying execution risk relative to any tiny edge. (3) Direction is genuinely unclear — there is no fundamental change to discount in either direction. (4) Right-side discipline says: if we cannot articulate a clear directional thesis with a confirmation trigger, we do not probe. Probing on noise is exactly the failure mode the framework guards against. (5) No portfolio context argues for action: we hold no MIDC or related industrials exposure that needs hedging or rebalancing.

SIZING: Not applicable — no probe is justified. If forced to act, the smallest defensible size would be a single share to mark a watchlist, but that is not a real bet and is excluded by the framework.

CONFIRMATION TRIGGERS that would change the call: a follow-on filing or news indicating the retirement is connected to operational issues, a guidance revision within the next few sessions, unusual options activity or a >2 sigma gap on the open Monday on heavy volume, or a Form 4 cluster suggesting insider concern. Absent these, this is a non-event.

EXIT/INVALIDATION: N/A since no position is opened. The thesis 'this is non-actionable noise' is invalidated only if the market price action or a subsequent filing reveals undisclosed adverse information.

#### Trial 3 full

FOR taking action: There is essentially no affirmative case here. The filing is a textbook Item 5.02 routine officer transition: long-tenured COO retiring on a pre-announced timeline, internal successor with nine years of company experience, outgoing executive staying on in an advisory role through fiscal year-end, and explicit language that no changes are being made to strategic plan, capital allocation, or operating outlook. None of the markers that make a 5.02 actionable are present — no abrupt departure, no 'for cause' language, no resignation without successor, no CFO/CEO departure, no mention of disagreements with the board, no concurrent guidance change, no Section 16 selling disclosure attached.

AGAINST taking action: The information content of this filing is near zero. A right-side, confirmation-first system should not initiate exposure on an event that does not even create a directional hypothesis. Acting here would burn one of the three open-position slots and consume daily notional budget on a name where we have no edge and no catalyst. The filing was also accepted at 17:45 ET, after the regular session close, so any immediate price reaction would occur in thin after-hours liquidity where slippage on a $500 probe is disproportionately high relative to expected signal.

Sizing: Not applicable — there is no defensible probe. The smallest meaningful position in MIDC at $45 would still be ~11 shares (~$495) which would expose capital to idiosyncratic noise with no thesis. The right-side principle here is to wait; there is nothing to confirm.

Confirmation triggers (if a thesis later emerged): Only revisit MIDC if (a) a follow-on 8-K or news item adds genuinely new information (guidance revision, strategic review, M&A, additional unexpected departures clustered with this one suggesting a pattern), or (b) price action shows an unusual multi-sigma move on volume that is itself the signal — at which point the trigger is the price/volume action, not this filing.

Invalidation: N/A since no position is proposed. If a hypothetical small probe were taken, invalidation would be any close back through the entry on declining volume, or any subsequent filing reaffirming the 'no change to outlook' language.

</details>