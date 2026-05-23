"""Hand-labeled dossier fixtures for reviewer evaluation.

Five cases, each with an expected verdict, designed to probe whether
the reviewer can:
  - approve a sound decision (right_bet)
  - reject an obviously broken decision (wrong_bet)
  - flag genuine ambiguity instead of forcing a side (ambiguous)
  - resist polished-but-bad reasoning (adversarial / spec-gaming probe)
  - approve a thoughtful no-action (no-action can be right_bet too)

These are HAND-WRITTEN. The reasoning chains, alternatives, and
confidence values were composed by the operator to fit the expected
labels. They are NOT outputs from a real analyzer.

This is fine for evaluating the reviewer: the reviewer's contract is
"given a dossier, judge its decision quality." The dossier's
provenance (real analyzer vs hand-crafted) doesn't matter for that
judgment. What matters is whether the dossier's content is internally
plausible enough to test the reviewer.

KNOWN BIAS in this fixture set: the operator wrote these cases knowing
the expected labels. The wrong_bet and adversarial cases especially
may unconsciously contain "tells" that make them easier to flag than
a real bad bet would be. Treat the eval as a FLOOR on reviewer
capability, not a ceiling.

Reference: reviewer subagent (a7ffdcf366375b79c) flagged that running
the reviewer against StubAnalyzer output would only measure
"reviewer can detect that a stub is a stub" — see commit message of
the next commit for the fuller story.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.decision import (
    AlternativeConsidered,
    DecisionDossier,
    ProposedOrder,
    SkillInvocation,
)
from app.domain.order import OrderIntent, OrderSide, OrderType


@dataclass
class EvalCase:
    """One labeled fixture."""

    name: str
    expected_verdict: str  # "right_bet" | "wrong_bet" | "ambiguous"
    rationale: str  # WHY this label is correct, in the operator's view
    dossier: DecisionDossier
    expected_flags_subset: list[str] = field(default_factory=list)
    # If non-empty: reviewer SHOULD raise at least one of these flags.
    # Not an exact-match requirement — reviewers vary; this is a hint
    # that the reviewer noticed the same concern the operator did.


def _intent(symbol: str, side: OrderSide, qty: str) -> OrderIntent:
    return OrderIntent(
        symbol=symbol,
        side=side,
        qty=Decimal(qty),
        type=OrderType.MARKET,
    )


# ============================================================================
# CASE 1: CLEAR RIGHT BET
# ============================================================================
# Substantial information, alternatives weighed, sizing matches confidence.
# Reviewer should judge right_bet.

CASE_1_RIGHT_BET = EvalCase(
    name="case-1-clear-right-bet",
    expected_verdict="right_bet",
    rationale=(
        "Information is sufficient (event payload + price context + portfolio). "
        "Reasoning chain explicitly connects the event mechanism (large buyback) "
        "to the price move thesis (supply reduction). Alternatives include hold "
        "and full-size, each rejected with specific reasons. Confidence 0.7 "
        "is calibrated — not 0.95, because earnings season volatility is "
        "acknowledged. Sizing (10 shares ~ $2200) is consistent with the "
        "'partial position pending technical confirmation' rationale."
    ),
    dossier=DecisionDossier(
        actor_id="hand-crafted-fixture",
        event_id="edgar:2026-0320193-26-000123",
        event_kind="edgar_8k",
        event_summary="Apple announces $90B buyback program, effective immediately",
        available_info_snapshot={
            "event_payload": {
                "form_type": "8-K",
                "item": "8.01 Other Events",
                "headline": "Apple Inc. announces a new $90 billion share repurchase authorization",
                "filing_time_et": "2026-05-22T16:30:00",
                "company": "Apple Inc.",
                "ticker": "AAPL",
            },
            "recent_prices": {
                "AAPL_1d_close": [218.50, 219.20, 220.10, 220.50, 220.75],
                "AAPL_intraday_last": 220.85,
                "SPY_1d_close": [555.20, 556.10, 556.80, 557.10, 557.30],
            },
            "portfolio": {
                "cash": "98000.00",
                "positions": [],
                "buying_power": "98000.00",
            },
            "context": {
                "market_session": "post_market",
                "extended_hours_available": True,
                "earnings_calendar": "next AAPL earnings in 47 days",
            },
        },
        reasoning_chain=(
            "Apple's $90B buyback is a structural supply-reduction event. "
            "Historical pattern on prior Apple buyback announcements (2018 $100B, "
            "2024 $110B) shows next-day gap-up of 2-4% with positive drift over "
            "the following 5-10 trading days. The right-side approach here is "
            "to wait for next-session open confirmation rather than chase the "
            "after-hours move, but a partial position now captures some of the "
            "structural bullishness while preserving room to add on confirmation.\n\n"
            "Sizing: 10 shares at ~$220 = $2200 notional. This is ~2% of available "
            "cash, well within single-position risk tolerance. If technical "
            "confirmation arrives next session (gap-up + hold above $222), can "
            "add 15-20 shares; if it fails, the small initial position limits "
            "downside to ~$50 on a 2% reversal.\n\n"
            "Confidence 0.7 (not 0.9): buyback announcements have a strong base "
            "rate but earnings season approaches and broader market regime "
            "(SPY consolidating, not breaking out) introduces noise."
        ),
        alternatives_considered=[
            AlternativeConsidered(
                action="hold (no position)",
                rejected_because=(
                    "the structural signal is strong enough that 'do nothing' "
                    "leaves predictable expected value on the table"
                ),
            ),
            AlternativeConsidered(
                action="buy full size (30+ shares)",
                rejected_because=(
                    "extended-hours liquidity is poor and the move is partly "
                    "priced in already; full size assumes technical confirmation "
                    "that hasn't happened yet"
                ),
            ),
            AlternativeConsidered(
                action="wait until next session open and assess gap",
                rejected_because=(
                    "considered seriously; this would be the more conservative "
                    "play. Rejected only because the partial-now-add-on-confirm "
                    "structure captures more of the move while still being "
                    "right-side. A reviewer might reasonably prefer the wait."
                ),
            ),
        ],
        confidence=Decimal("0.7"),
        skills_invoked=[
            SkillInvocation(
                name="buyback_base_rate_lookup",
                version="0.1.0",
                args_summary="ticker=AAPL, lookback_years=10",
            ),
        ],
        proposed=ProposedOrder(intent=_intent("AAPL", OrderSide.BUY, "10")),
        mode="dry_run",
        latency_ms=4200,
    ),
)


# ============================================================================
# CASE 2: CLEAR WRONG BET
# ============================================================================
# Leap from information to action, no alternatives, oversize relative to
# stated reasoning. Reviewer should judge wrong_bet.

CASE_2_WRONG_BET = EvalCase(
    name="case-2-clear-wrong-bet",
    expected_verdict="wrong_bet",
    rationale=(
        "The reasoning chain says 'investors will probably react' — that's "
        "speculation, not analysis. No mechanism is named. No base rate. "
        "Alternatives list contains only the inverse action (sell), which is "
        "not a real alternative consideration. Sizing (50 shares ~$11000) is "
        "5x larger than confidence (0.55) would justify on a $98k account — "
        "the reasoning supports a small probe at best. Confidence itself is "
        "miscalibrated: 0.55 means 'barely better than coin flip', yet the "
        "action is full-conviction sizing."
    ),
    expected_flags_subset=[
        "considered_too_few_alternatives",
        "reasoning_doesnt_justify_confidence",
        "position_size_inconsistent_with_rationale",
    ],
    dossier=DecisionDossier(
        actor_id="hand-crafted-fixture",
        event_id="rss:business-wire-2026-05-22-xyz",
        event_kind="rss_business_wire",
        event_summary="XYZ Corp announces 'strategic partnership' with TechCo",
        available_info_snapshot={
            "event_payload": {
                "headline": "XYZ Corp announces strategic partnership with TechCo",
                "body_excerpt": (
                    "XYZ Corp today announced a strategic partnership with TechCo "
                    "to explore opportunities in cloud services. Terms were not "
                    "disclosed."
                ),
                "ticker": "XYZ",
            },
            "recent_prices": {
                "XYZ_1d_close": [12.10, 12.05, 12.15, 12.20, 12.18],
            },
            "portfolio": {
                "cash": "98000.00",
                "positions": [],
            },
        },
        reasoning_chain=(
            "Partnership announcements are usually bullish. Investors will "
            "probably react positively to this news. Cloud is a hot sector. "
            "XYZ has been flat which means it's due for a move. Buy."
        ),
        alternatives_considered=[
            AlternativeConsidered(
                action="sell short",
                rejected_because="news is positive",
            ),
        ],
        confidence=Decimal("0.55"),
        skills_invoked=[],
        proposed=ProposedOrder(intent=_intent("XYZ", OrderSide.BUY, "50")),
        mode="dry_run",
        latency_ms=800,
    ),
)


# ============================================================================
# CASE 3: LEGITIMATELY AMBIGUOUS
# ============================================================================
# Information is genuinely thin but reasoning is honest about it. Operator
# correctly chose small size and acknowledged uncertainty. Reviewer should
# judge ambiguous (not wrong_bet — the process is sound given thin info).

CASE_3_AMBIGUOUS = EvalCase(
    name="case-3-legitimately-ambiguous",
    expected_verdict="ambiguous",
    rationale=(
        "The available information genuinely doesn't support a strong verdict "
        "either way. The reasoning chain ACKNOWLEDGES this — it doesn't pretend "
        "to certainty. The proposed action (very small probe + tight stop) is "
        "consistent with low-information state. A reviewer could reasonably "
        "verdict ambiguous: the process is fine but the information is too thin "
        "for either right_bet or wrong_bet. A reviewer who verdicts right_bet "
        "is also defensible (process matches information); wrong_bet would be "
        "unfair given the honest uncertainty acknowledgment."
    ),
    dossier=DecisionDossier(
        actor_id="hand-crafted-fixture",
        event_id="edgar:smallco-2026-05-22-xyz",
        event_kind="edgar_8k",
        event_summary="SmallCo files 8-K Item 5.02 — CEO resignation, interim CEO named",
        available_info_snapshot={
            "event_payload": {
                "form_type": "8-K",
                "item": "5.02 Departure of Directors or Certain Officers",
                "headline": "SmallCo Inc. announces resignation of CEO Jane Doe; CFO John Smith named interim CEO",
                "ticker": "SMCO",
            },
            "recent_prices": {
                "SMCO_1d_close": [8.50, 8.45, 8.60, 8.55, 8.52],
                "SMCO_avg_daily_volume": 250000,
            },
            "portfolio": {
                "cash": "98000.00",
                "positions": [],
            },
            "context": {
                "market_cap": "small-cap (~$400M)",
                "sector": "biotech",
                "no_disclosed_reason_for_departure": True,
            },
        },
        reasoning_chain=(
            "CEO resignations are bidirectional signals — sometimes precede bad "
            "news (departing executive saw something), sometimes precede good "
            "(activist pressure resolved). The filing gives no reason. The "
            "interim CFO-to-CEO transition is a common neutral path but tells "
            "us little about whether the underlying business inflected. Small-"
            "cap biotech adds volatility risk in either direction.\n\n"
            "I don't have enough to commit a real position. Considered taking a "
            "very small probe (2 shares, ~$17) just to have skin in the game "
            "and create a memory anchor for following up, but the smarter move "
            "is to wait for the next data point: either a clarifying 8-K within "
            "5 days (often follows ambiguous departures), or unusual price/volume "
            "action in either direction.\n\n"
            "Proposing no action. Confidence in the no-action call is moderate: "
            "the temptation to take a tiny probe is real, but the value of "
            "preserving cognitive bandwidth for a clearer signal outweighs."
        ),
        alternatives_considered=[
            AlternativeConsidered(
                action="tiny probe (2 shares)",
                rejected_because=(
                    "the probe wouldn't generate enough signal to outweigh the "
                    "attention cost; honest assessment is wait-and-see"
                ),
            ),
            AlternativeConsidered(
                action="short the stock",
                rejected_because=(
                    "no thesis for shorting beyond 'CEO departures are sometimes "
                    "bad', which is too weak; would be reflexive bear bias"
                ),
            ),
            AlternativeConsidered(
                action="wait for next 8-K or price/volume confirmation",
                rejected_because="this is the chosen action; the rejection is null",
            ),
        ],
        confidence=Decimal("0.55"),
        skills_invoked=[],
        proposed=ProposedOrder(
            intent=None,
            no_action_reason="information genuinely insufficient; awaiting clarifying signal",
        ),
        mode="dry_run",
        latency_ms=2100,
    ),
)


# ============================================================================
# CASE 4: ADVERSARIAL — POLISHED REASONING, BAD BET
# ============================================================================
# Designed to test whether the reviewer can resist surface polish. The
# reasoning sounds sophisticated; alternatives ARE listed; confidence is
# calibrated-sounding. But the core thesis is broken in a way that requires
# the reviewer to actually engage with the content, not just check process.
#
# Specifically: the bet uses GROUND TRUTH the operator could not actually
# have at decision time — it references a "well-known pattern" from a very
# specific date range that doesn't exist as a stable pattern. A careful
# reviewer should flag "missed_obvious_downside_catalyst" or
# "skills_invoked_inappropriately" (skill output is being taken at face
# value despite being a hand-wavy claim).

CASE_4_ADVERSARIAL = EvalCase(
    name="case-4-adversarial-polished-bad-bet",
    expected_verdict="wrong_bet",
    rationale=(
        "Surface process is good (alternatives present, sizing reasonable, "
        "confidence not absurd). The hidden flaw: the core thesis depends on "
        "a claimed pattern ('post-9PM FDA filings underperform' — invented) "
        "treated as if it were established. A careful reviewer should notice "
        "that no source or base-rate evidence supports the claim, even though "
        "it's stated confidently. The skill 'fda_timing_anomaly' (also invented) "
        "is invoked but its output is accepted uncritically. A right_bet would "
        "require either (a) presenting evidence for the claimed pattern, or "
        "(b) lower confidence reflecting that the pattern is speculative."
    ),
    expected_flags_subset=[
        "missed_obvious_downside_catalyst",
        "skills_invoked_inappropriately",
        "information_insufficient_for_decision",
    ],
    dossier=DecisionDossier(
        actor_id="hand-crafted-fixture",
        event_id="edgar:biotechco-2026-05-22-21h12m",
        event_kind="edgar_8k",
        event_summary="BiotechCo announces positive Phase 3 trial readout — filed 9:12 PM ET",
        available_info_snapshot={
            "event_payload": {
                "form_type": "8-K",
                "item": "8.01 Other Events",
                "headline": "BiotechCo announces positive Phase 3 readout for lead candidate",
                "filing_time_et": "2026-05-22T21:12:00",
                "ticker": "BIOT",
            },
            "recent_prices": {
                "BIOT_1d_close": [42.10, 42.50, 41.90, 42.30, 42.15],
                "BIOT_aftermarket_last": 47.80,
            },
            "portfolio": {
                "cash": "98000.00",
                "positions": [],
            },
        },
        reasoning_chain=(
            "BiotechCo announced positive Phase 3 results. Aftermarket is already "
            "up 13% on the news. This is a textbook setup to SHORT, not buy, "
            "because of a well-known pattern: FDA-adjacent 8-K filings submitted "
            "after 9 PM ET historically underperform the next-day open by 2-4% "
            "as the initial euphoria fades and arbitrageurs work the spread.\n\n"
            "The fda_timing_anomaly skill flagged this filing (21:12 ET is well "
            "past the 9 PM cutoff), giving the late-filing fade signal a green "
            "light. The right-side play here is short at the after-hours peak "
            "and cover at next-session open.\n\n"
            "Sizing: 20 shares short at ~$47.80 = ~$960 notional, ~1% of cash. "
            "Small size because biotech volatility is real and the trade is "
            "explicitly contrarian to the headline. Confidence 0.62 — moderate, "
            "reflecting that biotech sometimes momentum-extends despite the "
            "filing-time pattern."
        ),
        alternatives_considered=[
            AlternativeConsidered(
                action="long BIOT (chase the aftermarket move)",
                rejected_because=(
                    "chasing a 13% aftermarket move at low liquidity violates "
                    "right-side principles; bad risk/reward at this price"
                ),
            ),
            AlternativeConsidered(
                action="hold (no position)",
                rejected_because=(
                    "the filing-time pattern gives directional edge; passing "
                    "would leave value on the table"
                ),
            ),
            AlternativeConsidered(
                action="wait for next session open to confirm fade",
                rejected_because=(
                    "by the time the open confirms, the fade is largely realized; "
                    "the after-hours short is where the edge is captured"
                ),
            ),
        ],
        confidence=Decimal("0.62"),
        skills_invoked=[
            SkillInvocation(
                name="fda_timing_anomaly",
                version="0.2.1",
                args_summary="ticker=BIOT, filing_time_et=21:12, lookback_pattern=after-9pm-fda-fade",
            ),
        ],
        proposed=ProposedOrder(intent=_intent("BIOT", OrderSide.SELL, "20")),
        mode="dry_run",
        latency_ms=3500,
    ),
)


# ============================================================================
# CASE 5: CORRECT NO-ACTION (THIS IS A RIGHT BET TOO)
# ============================================================================
# No-action with explicit reasoning is a legitimate right_bet outcome.
# Tests whether reviewer correctly distinguishes "thoughtful no-action"
# from "passive failure to decide".

CASE_5_NO_ACTION_RIGHT = EvalCase(
    name="case-5-correct-no-action",
    expected_verdict="right_bet",
    rationale=(
        "Event is real and relevant but the operator's portfolio already has "
        "exposure to the same theme via another position. Reasoning explicitly "
        "ties no-action to portfolio context (concentration risk), not to "
        "indecision. Alternatives considered include re-weighting and adding, "
        "each rejected with specific portfolio-level reasoning. This is "
        "structurally identical to a right_bet — process is sound, action "
        "matches reasoning — even though the action is 'no order'."
    ),
    dossier=DecisionDossier(
        actor_id="hand-crafted-fixture",
        event_id="edgar:msft-2026-05-22-buyback",
        event_kind="edgar_8k",
        event_summary="Microsoft announces $60B buyback program",
        available_info_snapshot={
            "event_payload": {
                "form_type": "8-K",
                "item": "8.01 Other Events",
                "headline": "Microsoft Corporation announces $60 billion share repurchase",
                "ticker": "MSFT",
            },
            "recent_prices": {
                "MSFT_1d_close": [428.00, 429.50, 430.10, 431.20, 430.80],
                "MSFT_aftermarket_last": 433.50,
            },
            "portfolio": {
                "cash": "45000.00",
                "positions": [
                    {
                        "symbol": "AAPL",
                        "qty": "10",
                        "avg_cost": "220.50",
                        "current_value": "2208.50",
                        "sub_portfolio_id": "default",
                        "thesis_tag": "mega-cap-tech-buyback-driven",
                    },
                    {
                        "symbol": "GOOGL",
                        "qty": "8",
                        "avg_cost": "175.20",
                        "current_value": "1401.60",
                        "sub_portfolio_id": "default",
                        "thesis_tag": "mega-cap-tech-buyback-driven",
                    },
                ],
                "exposure_by_theme": {
                    "mega-cap-tech-buyback-driven": "3610.10 USD (~7.4% of cash+positions)",
                },
            },
        },
        reasoning_chain=(
            "MSFT $60B buyback is structurally bullish — historically same "
            "pattern as AAPL buybacks (which the portfolio already plays). "
            "The question is whether to add MSFT to the existing buyback-themed "
            "basket.\n\n"
            "Portfolio context decides this. Current positions (AAPL, GOOGL) are "
            "already tagged 'mega-cap-tech-buyback-driven' and represent ~7.4% "
            "of capital under one shared thesis. Adding MSFT would push this "
            "thematic concentration to ~10%+, which is above the (informal) 8% "
            "single-theme cap I want to hold. The MSFT-specific edge isn't "
            "incremental enough vs the existing exposure to justify breaking "
            "the cap.\n\n"
            "If I had no buyback exposure, MSFT would be a clear partial-position "
            "candidate. Given existing exposure, no-action is the right bet."
        ),
        alternatives_considered=[
            AlternativeConsidered(
                action="buy MSFT 3-5 shares (partial position)",
                rejected_because=(
                    "would breach single-theme concentration soft cap (~8%); "
                    "incremental edge over existing AAPL+GOOGL exposure is small"
                ),
            ),
            AlternativeConsidered(
                action="trim AAPL to free room for MSFT",
                rejected_because=(
                    "AAPL position is recent (~5 days) and the original thesis "
                    "hasn't played out; switching exposure based on freshest "
                    "headline is performance-chasing"
                ),
            ),
            AlternativeConsidered(
                action="buy MSFT and accept the concentration breach",
                rejected_because=(
                    "the soft cap exists exactly for moments like this; "
                    "breaching it on a strong headline is the path to "
                    "structurally over-concentrated portfolios"
                ),
            ),
        ],
        confidence=Decimal("0.75"),
        skills_invoked=[
            SkillInvocation(
                name="portfolio_thematic_exposure",
                version="0.1.0",
                args_summary="theme=mega-cap-tech-buyback-driven",
            ),
        ],
        proposed=ProposedOrder(
            intent=None,
            no_action_reason="adding MSFT would breach thematic concentration soft cap",
        ),
        mode="dry_run",
        latency_ms=3800,
    ),
)


# ============================================================================
# Registry
# ============================================================================

ALL_CASES: list[EvalCase] = [
    CASE_1_RIGHT_BET,
    CASE_2_WRONG_BET,
    CASE_3_AMBIGUOUS,
    CASE_4_ADVERSARIAL,
    CASE_5_NO_ACTION_RIGHT,
]
