"""
Consensus — weighted aggregation, risk controls, synthetic debate.
Ported from lib/engine/consensus.ts
"""

from typing import Dict, List, Any, Optional
from scan_pipeline.engines.personality import (
    AIPersonality,
    generate_opening_statement,
    generate_rebuttal,
    ConversationTurn,
    realized_hit_rates,
)
from scan_pipeline.config.tickers import ENGINE_CONFIG

# Rolling-accuracy dampener floor: a persona at 0% trailing realized hit rate
# keeps 25% of its raw vote — cold streaks discount a vote, never zero it.
HIT_RATE_FLOOR = 0.25

# Per-sponsor exposure cap on the final book. Weight freed by the cap is NOT
# redistributed; tracker.py books the residual as cash (weights may sum < 1).
MAX_AGENT_EXPOSURE = 0.40


def _dampened_accuracy(name: str, accuracy: float, hit_rates: Dict[str, float]) -> float:
    """Dampener f(hit_rate) = max(0.25, hit_rate), applied pre-normalization.

    Sponsors with no realized history yet are unpenalized (factor 1.0).
    """
    hit_rate = hit_rates.get(name)
    if hit_rate is None:
        return accuracy
    return accuracy * max(HIT_RATE_FLOOR, hit_rate)


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

    cecil_accuracy = cecil.stats.picksAccuracy if cecil else 0.33
    marky_accuracy = marky.stats.picksAccuracy if marky else 0.33
    ophelia_accuracy = ophelia.stats.picksAccuracy if ophelia else 0.33

    # Dampen raw accuracies by trailing realized hit rate BEFORE normalization.
    hit_rates = realized_hit_rates()
    cecil_accuracy = _dampened_accuracy("Cecil", cecil_accuracy, hit_rates)
    marky_accuracy = _dampened_accuracy("Marky", marky_accuracy, hit_rates)
    ophelia_accuracy = _dampened_accuracy("Ophelia", ophelia_accuracy, hit_rates)

    total_accuracy = cecil_accuracy + marky_accuracy + ophelia_accuracy
    if total_accuracy == 0:
        total_accuracy = 1.0
    cecil_weight = cecil_accuracy / total_accuracy
    marky_weight = marky_accuracy / total_accuracy
    ophelia_weight = ophelia_accuracy / total_accuracy

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

    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: v / total for k, v in adjusted.items()}

    # Per-sponsor exposure cap: no agent may hold more than 40% of the book.
    # Offending sponsors are scaled down pro-rata (their picks keep their
    # relative proportions). The freed weight is deliberately NOT
    # redistributed: the book may sum to < 1 and tracker.py books the
    # residual as cash. At most 3 sponsors, so 3 passes always converge.
    if attribution:
        for _ in range(3):
            sponsor_totals: Dict[str, float] = {}
            for ticker, weight in adjusted.items():
                sponsor = attribution.get(ticker)
                if sponsor:
                    sponsor_totals[sponsor] = sponsor_totals.get(sponsor, 0.0) + weight
            over = {s: t for s, t in sponsor_totals.items() if t > MAX_AGENT_EXPOSURE + 1e-9}
            if not over:
                break
            for sponsor, sponsor_total in over.items():
                scale = MAX_AGENT_EXPOSURE / sponsor_total
                for ticker in adjusted:
                    if attribution.get(ticker) == sponsor:
                        adjusted[ticker] *= scale

    return adjusted
