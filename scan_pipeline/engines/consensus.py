"""
Consensus — weighted aggregation, risk controls, synthetic debate.
Ported from lib/engine/consensus.ts
"""

from typing import Dict, List, Any, Optional
import os

from scan_pipeline.engines.personality import (
    AIPersonality,
    realized_hit_counts,
    generate_opening_statement,
    generate_rebuttal,
    ConversationTurn,
)
from scan_pipeline.config.tickers import ENGINE_CONFIG

# Merit weighting (rewritten 2026-09-13).
#
# The vote used to be picksAccuracy * max(HIT_RATE_FLOOR, realized_hit_rate).
# Those are two measures of the SAME quantity -- picksAccuracy is an EMA of
# realized weekly hit rates, realized_hit_rate is the pooled fraction -- so
# multiplying them squared the signal. Third instance of the same
# double-counting bug (pick_confidence x consensus dampener was the first).
# It produced a 4.50x Cecil:Marky vote ratio out of 24 closed positions whose
# Wilson intervals -- [0.27,0.73], [0.00,0.39], [0.05,0.70] -- overlap almost
# entirely. The data cannot tell these three agents apart; the weighting said
# otherwise with great confidence.
#
# One measure now, shrunk toward the pooled hit rate in proportion to how
# little evidence the agent actually has:
#
#     weight_i  proportional to  (hits_i + K * pooled) / (total_i + K)
#
# K is the prior's strength in pseudo-observations. K=0 is the raw rate and
# silences a 0-for-6 agent outright; K=10 gives Cecil:Marky 2.07x; K=24 (prior
# worth as much as the whole record) gives 1.48x. An agent with no closed
# history lands exactly on the prior instead of an arbitrary floor -- which is
# why the old hard floor is gone: shrinkage does that job continuously and
# scales with evidence rather than ignoring it.
MERIT_PRIOR_STRENGTH = float(os.environ.get("COUNCIL_MERIT_PRIOR", "10") or 10)

# Per-sponsor exposure cap on the final book. Weight freed by the cap is NOT
# redistributed; tracker.py books the residual as cash (weights may sum < 1).
MAX_AGENT_EXPOSURE = 0.40


def merit_weights(names, counts=None, prior_strength: Optional[float] = None) -> Dict[str, float]:
    """Normalized vote weights, empirical-Bayes shrunk toward the pooled rate.

    Equal weights when there is no closed history at all: with no evidence, no
    agent has earned a bigger vote than another.
    """
    names = list(names)
    if not names:
        return {}
    K = MERIT_PRIOR_STRENGTH if prior_strength is None else prior_strength
    counts = realized_hit_counts() if counts is None else counts

    hits = sum(h for h, _ in counts.values())
    total = sum(n for _, n in counts.values())
    if total <= 0:
        return {n: 1.0 / len(names) for n in names}
    pooled = hits / total

    raw = {}
    for name in names:
        h, n = counts.get(name, (0, 0))
        raw[name] = (h + K * pooled) / (n + K) if (n + K) > 0 else pooled
    s = sum(raw.values())
    if s <= 0:
        return {n: 1.0 / len(names) for n in names}
    return {n: v / s for n, v in raw.items()}


class ConsensusResult:
    def __init__(
        self,
        portfolio: Dict[str, float],
        attribution: Dict[str, str],
        reasoning: str,
        confidence: float,
        conversation: List[ConversationTurn],
    ):
        self.portfolio = portfolio
        self.attribution = attribution
        self.reasoning = reasoning
        self.confidence = confidence
        self.conversation = conversation

    def to_dict(self) -> dict:
        return {
            "portfolio": self.portfolio,
            "attribution": self.attribution,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "conversation": [c.to_dict() for c in self.conversation],
        }


def aggregate(
    cecil_proposal: Dict[str, Any],
    marky_proposal: Dict[str, Any],
    ophelia_proposal: Dict[str, Any],
    personas: Dict[str, AIPersonality]
) -> ConsensusResult:
    """
    Aggregate three agent proposals into a weighted consensus top-5 portfolio.
    """
    cecil = personas.get("Cecil")
    marky = personas.get("Marky")
    ophelia = personas.get("Ophelia")

    # Single shrunk merit measure. picksAccuracy is still maintained on the
    # persona and still reported; it is simply no longer multiplied by a second
    # estimate of the same thing. See MERIT_PRIOR_STRENGTH above.
    _w = merit_weights(["Cecil", "Marky", "Ophelia"])
    cecil_weight = _w["Cecil"]
    marky_weight = _w["Marky"]
    ophelia_weight = _w["Ophelia"]
    print("[consensus] vote weights (prior K=%g): Cecil %.1f%% / Ophelia %.1f%% / Marky %.1f%%"
          % (MERIT_PRIOR_STRENGTH, cecil_weight * 100, ophelia_weight * 100, marky_weight * 100))

    scores: Dict[str, Dict[str, Any]] = {}

    def add_proposal(proposal: Dict[str, Any], weight: float):
        agent = proposal["agent"]
        for idx, stock in enumerate(proposal.get("stocks", [])):
            ticker = stock["ticker"]
            rank_multiplier = 3 - idx
            current = scores.get(ticker, {"score": 0.0, "sponsors": {}})
            contribution = stock["confidence"] * weight * rank_multiplier
            current["score"] += contribution
            if agent not in current["sponsors"]:
                current["sponsors"][agent] = {"confidence": stock["confidence"], "contribution": contribution}
            else:
                current["sponsors"][agent]["contribution"] += contribution
            scores[ticker] = current

    add_proposal(cecil_proposal, cecil_weight)
    add_proposal(marky_proposal, marky_weight)
    add_proposal(ophelia_proposal, ophelia_weight)

    sorted_stocks = []
    for ticker, data in scores.items():
        primary_sponsor = "Cecil"
        max_contribution = float("-inf")
        for agent, sponsor_data in data["sponsors"].items():
            if sponsor_data["contribution"] > max_contribution:
                max_contribution = sponsor_data["contribution"]
                primary_sponsor = agent
        primary_confidence = data["sponsors"].get(primary_sponsor, {}).get("confidence", 0.0)
        sorted_stocks.append({
            "ticker": ticker,
            "score": data["score"],
            "primary_sponsor": primary_sponsor,
            "primary_confidence": primary_confidence
        })

    sorted_stocks.sort(key=lambda s: s["score"], reverse=True)
    top5 = sorted_stocks[:5]

    raw_portfolio = {}
    total_score = sum(s["score"] for s in top5)
    for s in top5:
        raw_portfolio[s["ticker"]] = s["score"] / total_score if total_score > 0 else 0.0

    # Sponsor attribution must exist before risk controls (per-agent cap).
    attribution = {}
    for s in top5:
        attribution[s["ticker"]] = s["primary_sponsor"]

    portfolio = _enforce_risk_controls(raw_portfolio, attribution)

    avg_confidence = sum(s["primary_confidence"] for s in top5) / len(top5) if top5 else 0.0
    confidence = avg_confidence / 100.0

    winners = ", ".join(s["ticker"] for s in top5)
    reasoning = (
        f"The Council has converged on {winners} through a weighted consensus. "
        "Cecil brings fundamental value, Marky reads the technicals, and Ophelia watches the macro tide."
    )

    conversation: List[ConversationTurn] = []
    if cecil and cecil_proposal.get("stocks"):
        conversation.append(generate_opening_statement(cecil, cecil_proposal["stocks"][0]))
    if marky and marky_proposal.get("stocks"):
        conversation.append(generate_opening_statement(marky, marky_proposal["stocks"][0]))
    if ophelia and ophelia_proposal.get("stocks"):
        conversation.append(generate_opening_statement(ophelia, ophelia_proposal["stocks"][0]))

    if cecil and marky_proposal.get("stocks"):
        conversation.append(generate_rebuttal(cecil, marky, marky_proposal["stocks"][0]))
    if marky and ophelia_proposal.get("stocks"):
        conversation.append(generate_rebuttal(marky, ophelia, ophelia_proposal["stocks"][0]))
    if ophelia and cecil_proposal.get("stocks"):
        conversation.append(generate_rebuttal(ophelia, cecil, cecil_proposal["stocks"][0]))

    return ConsensusResult(
        portfolio=portfolio,
        attribution=attribution,
        reasoning=reasoning,
        confidence=confidence,
        conversation=conversation
    )


def _enforce_risk_controls(portfolio: Dict[str, float],
                           attribution: Optional[Dict[str, str]] = None) -> Dict[str, float]:
    MAX_ALLOCATION = ENGINE_CONFIG["max_position_size"]
    MIN_ALLOCATION = ENGINE_CONFIG.get("min_position_size", 0.0)

    adjusted = dict(portfolio)

    # Iterate: normalize -> cap at MAX -> drop below-MIN positions, until stable.
    # (A single cap-then-renormalize can push names back above the cap.)
    for _ in range(10):
        total = sum(adjusted.values())
        if total <= 0:
            return {}
        adjusted = {k: v / total for k, v in adjusted.items()}

        changed = False
        if any(v > MAX_ALLOCATION + 1e-9 for v in adjusted.values()):
            adjusted = {k: min(v, MAX_ALLOCATION) for k, v in adjusted.items()}
            changed = True

        if MIN_ALLOCATION > 0:
            small = [k for k, v in adjusted.items() if v < MIN_ALLOCATION - 1e-9]
            if small and len(adjusted) - len(small) >= 1:
                for k in small:
                    del adjusted[k]
                changed = True

        if not changed:
            break

    # MAX-CAP ORDERING FIX (2026-09-13). This used to be a plain
    # `v / total` renormalisation to sum 1.0, which pushed every position back
    # over MAX_ALLOCATION -- the loop above caps, this undid the cap. With
    # fewer than ceil(1/MAX_ALLOCATION) names the two constraints cannot both
    # hold and the renormalise won silently (a two-name book came out at 50%
    # per position against a 30% cap). The fixed 0.40 sponsor cap below used
    # to mask it by scaling a one-sponsor bloc down first; the adaptive cap
    # lifts that mask, so the latent bug would have become a live one.
    #
    # A position limit means the book holds at most n * MAX_ALLOCATION. Scale
    # toward fully invested, but stop when the largest position reaches the
    # cap. The remainder is cash.
    total = sum(adjusted.values())
    if total > 0:
        largest = max(adjusted.values())
        scale = 1.0 / total
        if largest > 0:
            scale = min(scale, MAX_ALLOCATION / largest)
        adjusted = {k: v * scale for k, v in adjusted.items()}

    # Per-sponsor exposure cap: no agent may hold more than 40% of the book.
    # Offending sponsors are scaled down pro-rata (their picks keep their
    # relative proportions). The freed weight is deliberately NOT
    # redistributed: the book may sum to < 1 and tracker.py books the
    # residual as cash. At most 3 sponsors, so 3 passes always converge.
    if attribution:
        # ADAPTIVE SPONSOR CAP (2026-09-13). A fixed 0.40 with no
        # redistribution is a cash mandate, not a diversification rule: the
        # weight freed by the cap is never reallocated, so a book whose top 5
        # all carry one sponsor could never exceed 40% invested however good
        # the picks were. Observed consequence -- as the hit-rate dampener
        # progressively silenced Marky and Ophelia, sponsor diversity
        # collapsed and the book went 100% invested (2026-07-20, three
        # sponsors) -> 39.9% (2026-08-24, one sponsor) -> 26.6% (2026-08-31,
        # one sponsor). That is a feedback loop, not a risk control.
        #
        # 1/n_sponsors is the smallest cap that leaves the book
        # mathematically investable; the 0.40 floor preserves the original
        # intent once all three sponsors are actually contributing.
        sponsors = {attribution.get(t) for t in adjusted if attribution.get(t)}
        agent_cap = max(MAX_AGENT_EXPOSURE, 1.0 / max(len(sponsors), 1))
        for _ in range(3):
            sponsor_totals: Dict[str, float] = {}
            for ticker, weight in adjusted.items():
                sponsor = attribution.get(ticker)
                if sponsor:
                    sponsor_totals[sponsor] = sponsor_totals.get(sponsor, 0.0) + weight
            over = {s: t for s, t in sponsor_totals.items() if t > agent_cap + 1e-9}
            if not over:
                break
            for sponsor, sponsor_total in over.items():
                scale = agent_cap / sponsor_total
                for ticker in adjusted:
                    if attribution.get(ticker) == sponsor:
                        adjusted[ticker] *= scale

        # ORDERING FIX (2026-09-13). The normalize -> cap -> drop loop above
        # enforced MIN_ALLOCATION, but the sponsor scaling runs AFTER it and
        # never re-checked, so a capped book could hold positions below the
        # floor it had just enforced (five equal one-sponsor names landed at
        # 8.0% against a 10% floor). Drop without renormalising: the freed
        # weight becomes cash, consistent with how the cap already behaves,
        # and the pass terminates because nothing is scaled back up.
        if MIN_ALLOCATION > 0:
            small = [k for k, v in adjusted.items() if v < MIN_ALLOCATION - 1e-9]
            if small and len(adjusted) - len(small) >= 1:
                for k in small:
                    del adjusted[k]

    return adjusted
