"""
Marky — Technical Analysis Engine
Ported from lib/engine/technical.ts
"""

import json
import os
from typing import Dict, List, Any, Optional
from scan_pipeline.config.tickers import STOCK_UNIVERSE
from scan_pipeline.utils.data_utils import (
    get_sector,
    get_price_history,
    compute_simple_ma,
    compute_std_dev,
    compute_4_week_return,
    pick_confidence,
    avg_dollar_volume,
    log_ties,
    clamp,
    parse_vix,
)
from scan_pipeline.utils import wiki_signals

# --- 10Y duration gate (Agent C swarm fix) ----------------------------------
# The low-vol sleeve is a stealth long-duration bet for rate-sensitive
# sectors: it picked VTR -7.04% and ADBE -7.85% into a 4.7% 10Y regime.
# The gate reads the canonical macro fact table; a missing or unreadable
# file turns the gate OFF (graceful fallback).
_MACRO_FACTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "truth_gate", "macro", "facts.json",
)
_RATE_SENSITIVE_SECTORS = {"Real Estate", "Utilities"}
_TEN_Y_GATE_PCT = 4.5
_ten_y_cache: Optional[float] = None
_ten_y_loaded = False


def load_10y_yield() -> Optional[float]:
    """10Y UST yield in percent from truth_gate/macro/facts.json.

    Returns None (gate off) when the file is missing or malformed.
    Cached per process.
    """
    global _ten_y_cache, _ten_y_loaded
    if not _ten_y_loaded:
        _ten_y_loaded = True
        try:
            with open(_MACRO_FACTS_PATH, "r", encoding="utf-8") as f:
                facts = json.load(f)
            _ten_y_cache = float(facts["rates"]["ust_10y"]["value"])
        except Exception:
            _ten_y_cache = None
    return _ten_y_cache


def analyze(market_data: Dict[str, Any], date: str, price_cache: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
    """
    Analyze all tickers and return Marky's top-3 proposal.
    """
    vix = parse_vix(market_data.get("vix"))
    signals = wiki_signals.get_signals()
    ten_y = load_10y_yield()

    scores = []
    for ticker in STOCK_UNIVERSE:
        sector = get_sector(ticker)
        # (d) Vol/trend windows lengthened 4 -> 12 weeks. data_utils returns
        # whatever history exists, so short tapes degrade to what is there.
        history = get_price_history(ticker, date, 12, price_cache)
        window_weeks = len(history)
        recent = history[-4:] if window_weeks >= 4 else history
        closes = [h.close for h in history]
        returns = [h.return_ for h in history]
        four_week_return = compute_4_week_return(recent)
        ma = compute_simple_ma(closes)
        latest_close = closes[-1] if closes else 0.0
        std_dev = compute_std_dev(returns)  # None when history < 2 weeks

        # Trend: distance of the latest close from the (up to) 12-week MA.
        # -2% below the MA scores 0; +6% above scores 30; smooth in between.
        if ma > 0 and latest_close > 0:
            dist_ma = (latest_close - ma) / ma
            trend_score = 30.0 * clamp((dist_ma + 0.02) / 0.08, 0.0, 1.0)
        else:
            dist_ma = None
            trend_score = 0.0

        # (b) Two-sided momentum. Full marks for a healthy +5%..+20% 4W
        # rally; ramp-up below +5%; linear decay above +20% (zero at +40%);
        # minus an overextension penalty when price is stretched more than
        # +6% above its MA. A +25% vertical no longer banks a free 40.
        if four_week_return <= 0.0:
            momentum_base = 0.0
        elif four_week_return < 0.05:
            momentum_base = 40.0 * (four_week_return / 0.05)
        elif four_week_return <= 0.20:
            momentum_base = 40.0
        else:
            momentum_base = 40.0 * max(0.0, 1.0 - (four_week_return - 0.20) / 0.20)
        overext_penalty = 0.0
        if dist_ma is not None and dist_ma > 0.06:
            overext_penalty = 10.0 * clamp((dist_ma - 0.06) / 0.06, 0.0, 1.0)
        momentum_score = max(0.0, momentum_base - overext_penalty)

        # Volatility: calm tape (std 0) scores 30, wild tape (std >= 10%)
        # scores 0. None = insufficient history: neutral 10, no reward for
        # a blank tape.
        if std_dev is None:
            volatility_score = 10.0
        else:
            volatility_score = 30.0 * clamp((0.10 - std_dev) / 0.10, 0.0, 1.0)

        # (a) 10Y duration gate on the low-vol sleeve. Above the gate,
        # rate-sensitive sectors (REITs, Utilities) get zero low-vol
        # credit; an unknown sector gets a half discount, logged. Gate is
        # off when facts.json is unavailable.
        duration_gate = "off"
        if ten_y is not None and ten_y > _TEN_Y_GATE_PCT:
            if sector in _RATE_SENSITIVE_SECTORS:
                volatility_score = 0.0
                duration_gate = "zeroed"
            elif sector == "Unknown":
                volatility_score *= 0.5
                duration_gate = "partial-unknown-sector"
                print(f"[duration-gate] Marky: {ticker} sector unknown; low-vol score halved (10Y {ten_y:.2f}%)")

        # (c) Volume confirmation. A rally on rising dollar volume earns
        # +5; a rally on fading volume is a divergence, -5. No volume data
        # or no rally = 0. avg_dollar_volume stays in the sort tie-break.
        adv = avg_dollar_volume(history)
        volume_score = 0.0
        volume_trend = "unknown"
        if window_weeks >= 4:
            half = window_weeks // 2
            early_dv = avg_dollar_volume(history[:half])
            late_dv = avg_dollar_volume(history[half:])
            if early_dv and late_dv and early_dv > 0:
                dv_ratio = late_dv / early_dv
                if dv_ratio > 1.05:
                    volume_trend = "rising"
                elif dv_ratio < 0.95:
                    volume_trend = "fading"
                else:
                    volume_trend = "flat"
                if four_week_return > 0:
                    if volume_trend == "rising":
                        volume_score = 5.0
                    elif volume_trend == "fading":
                        volume_score = -5.0

        total_score = momentum_score + trend_score + volatility_score + volume_score
        # Nudge from the sector wikis: sector sentiment + direct mentions
        total_score = wiki_signals.adjusted_score(ticker, total_score, signals)

        scores.append({
            "ticker": ticker,
            "score": total_score,
            "momentum_score": momentum_score,
            "trend_score": trend_score,
            "volatility_score": volatility_score,
            "volume_score": volume_score,
            "four_week_return": four_week_return,
            "dist_ma": dist_ma,
            "std_dev": std_dev,
            "avg_dollar_volume": adv,
            "sector": sector,
            "window_weeks": window_weeks,
            "volume_trend": volume_trend,
            "duration_gate": duration_gate,
            "ten_y_yield": ten_y,
        })

    # Sort by score, then actual 4-week momentum, then realized volatility
    # (calmer beats jumpier; unknown history ranks last). Surviving ties break
    # by the documented order: synthesis watchlist -> wiki mentions ->
    # liquidity -> alphabetical (stable pre-sort). Never arbitrary, never a
    # rotating hash.
    scores.sort(key=lambda s: s["ticker"])
    scores.sort(
        key=lambda s: (
            s["score"],
            s["four_week_return"],
            -s["std_dev"] if s["std_dev"] is not None else float("-inf"),
            1 if s["ticker"] in signals.watchlist else 0,
            signals.mentions.get(s["ticker"], 0),
            s["avg_dollar_volume"] or 0.0,
        ),
        reverse=True,
    )
    tie_logs = log_ties(scores, "Marky", signals.watchlist, signals.mentions)
    for line in tie_logs:
        print(line)
    top3 = scores[:3]

    stocks = []
    for idx, s in enumerate(top3):
        next_score = scores[idx + 1]["score"] if idx + 1 < len(scores) else None
        # Pick-level conviction: the pick's own momentum, MA distance, and
        # realized volatility — not a constant, not a saturated bucket score.
        strength = (
            0.45 * clamp(s["four_week_return"] / 0.10, 0.0, 1.0)
            + 0.30 * clamp(((s["dist_ma"] if s["dist_ma"] is not None else -0.02) + 0.02) / 0.08, 0.0, 1.0)
            + 0.25 * (1.0 - clamp(s["std_dev"] / 0.10, 0.0, 1.0) if s["std_dev"] is not None else 0.5)
        )
        margin = 0.0
        if next_score is not None and s["score"] > next_score:
            margin = min(5.0, (s["score"] - next_score) * 0.25)
        conf_raw, conf = pick_confidence(strength, idx, vix, margin, persona="Marky")
        stocks.append({
            "ticker": s["ticker"],
            "confidence": conf,
            "confidence_raw": round(conf_raw, 2),
            "thesis": _generate_thesis(s, idx),
        })

    # Degeneracy meter: scores rounded to 2 decimals — real continuous signals
    # do not cluster at that granularity; bucketed/broken ones do.
    top_key = round(top3[0]["score"], 2) if top3 else None
    tied_at_top = sum(1 for s in scores if round(s["score"], 2) == top_key) if top3 else 0
    return {"agent": "Marky", "stocks": stocks, "tied_at_top": tied_at_top}


def _generate_thesis(s: dict, idx: int) -> str:
    vol_pct = "N/A" if s["std_dev"] is None else f"{s['std_dev'] * 100:.1f}%"
    window = s.get("window_weeks", 4)
    templates = [
        f"Strong momentum breaking above the {window}-week MA. 4W return: {s['four_week_return'] * 100:.1f}%.",
        f"Low volatility uptrend with clean price action. Vol: {vol_pct}. Score: {s['score']:.0f}.",
        f"Technical breakout with volume {s.get('volume_trend', 'unknown')}. Score: {s['score']:.0f}.",
    ]
    thesis = templates[idx % len(templates)]
    if s.get("duration_gate") == "zeroed" and s.get("ten_y_yield") is not None:
        thesis += f" Low-vol credit gated off (10Y {s['ten_y_yield']:.2f}%)."
    return thesis
