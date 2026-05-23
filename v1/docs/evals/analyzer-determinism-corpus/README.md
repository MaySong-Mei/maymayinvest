# Analyzer determinism corpus

Per amendment `2026-05-23-amend-bin3-rule-defer-aggregator.md` (approved).

Each event becomes ONE markdown file here. Filename: `<YYYY-MM-DD>-<event-slug>.md`. Each entry captures N=3 analyzer trials over the same event + the operator's manual pick.

## How to add an entry

```bash
python scripts/capture_event_to_corpus.py --event tests/fixtures/<event>.json [--aapl-price 220.50]
```

This writes the markdown stub. Then **open the stub and fill in the "Operator's manual pick" section by hand** before committing.

## Goal

Accumulate K=10 entries. At K=10 the operator examines aggregate disagreement rate and decides whether to build an aggregator (and if so, what kind). See amendment file for the decision rules at K=10.

## Discipline

- One commit per entry.
- Operator fills the pick BEFORE looking at any next-loop information (price action, reviewer judgment, etc).
- No cherry-picking events. If you ran capture on an event, commit it.

## Corpus design (locked before K=1, per reviewer a706acdb61967e260 steer)

**Fixture diversity required.** K=10 must span at least 3 different 8-K event classes; otherwise we'd land at K=10 with one-dimensional evidence (10 AAPL-shaped buyback events answer "does AAPL split?" not "is disagreement event-class-specific?").

Target shortlist for K=10:
1. **Buyback + earnings beat** — already have `edgar_8k_aapl_buyback_2024.json`. Ambiguous: real positive signal but post-close. (1-2 events)
2. **Clearly actionable** — material partnership / large contract win / FDA approval (clean positive catalyst). (2-3 events)
3. **Clearly non-actionable** — bylaw amendment / officer departure with named successor / routine 10-Q item ref. (2-3 events)
4. **Mixed / surprise** — guidance miss with capital return / leadership change with positive context. (1-2 events)
5. **Edge cases** — small-cap biotech FDA decision / late-filed 8-K / amendment-to-prior-filing. (1-2 events)

Operator curates fixtures incrementally — does NOT need to write all K=10 fixtures up front. But each new fixture must check the diversity box: don't add another buyback if class 1 is already represented and class 3 is empty.

**Re-capture policy: ONE EVENT = ONE MARKDOWN. Closed.**
- Filename: `<YYYY-MM-DD-of-first-capture>-<event-slug>.md`. Set once.
- If the operator wants to test whether disagreement is stable across days (re-running analyzer 3x on the same event a week later), that is a DIFFERENT experiment and goes in a different doc, NOT a second corpus entry.
- Rationale: corpus measures "what does the analyzer do on a fresh event" — a re-run is no longer a fresh event because the operator has already seen the first 3 dossiers.
