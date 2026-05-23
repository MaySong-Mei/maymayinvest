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
