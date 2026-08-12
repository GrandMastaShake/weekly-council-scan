"""
Ophelia — Macro Analysis Engine
Ported from lib/engine/macro.ts
"""

import math
from typing import Dict, List, Any, Optional
from scan_pipeline.config.tickers import STOCK_UNIVERSE
from scan_pipeline.utils.data_utils import (
    get_sector,
    get_price_history,
    compute_std_dev,
    compute_4_week_return,
    pick_confidence,
    avg_dollar_volume,
    log_ties,
    clamp,
    parse_vix,
    week_hash,
)
from scan_pipeline.utils import wiki_signals


def analyze(market_data: Dict[str, Any], date: str, price_cache: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
    """
    Analyze all tickers and return Ophelia's top-3 proposal.

    Additive output keys (consumed defensively by run_scan.py via .get()):
      data_degraded / data_degraded_reasons -- loud-fail flags (Fix C-d).
        A flag was chosen over raising an exception so the runner can treat
        it as a degenerate-mode abort condition.
      tie_broken_by / tie_resolvable -- tie-break metadata (Fix C-a).
      market_regime -- "bullish" / "bearish" / "rangebound" (Fix C-c).
    """
    vix = parse_vix(market_data.get("vix"))
    signals = wiki_signals.get_signals()
    weekly_returns = market_data.get("weeklyReturns", {})

    # Sector rotation base: the week BEFORE the latest completed week, read
    # straight from price history. Robust to whatever weekday the scan runs
    # on (the old exact-date lookup missed whenever the scan date wasn't a
    # Friday and left every sector "Unknown").
    sector_returns: Dict[str, List[float]] = {}
    for ticker in STOCK_UNIVERSE:
        sector = get_sector(ticker)
        history = get_price_history(ticker, date, 2, price_cache)
        if len(history) >= 2:
            sector_returns.setdefault(sector, []).append(history[-2].return_)
        elif len(history) == 1:
            sector_returns.setdefault(sector, []).append(history[-1].return_)

    sector_avg_returns = {}
    for sector, returns in sector_returns.items():
        sector_avg_returns[sector] = sum(returns) / len(returns)

    sorted_sectors = sorted(sector_avg_returns.items(), key=lambda x: x[1], reverse=True)
    top_sector = sorted_sectors[0][0] if sorted_sectors else "Unknown"
    second_sector = sorted_sectors[1][0] if len(sorted_sectors) > 1 else "Unknown"

    spy_history = get_price_history("SPY", date, 4, price_cache)
    spy_returns = [h.return_ for h in spy_history]
    spy_4w_return = compute_4_week_return(spy_history)
    spy_vol = compute_std_dev(spy_returns)  # None when SPY history < 2 weeks

    # (d) Loud-fail on empty inputs. An empty SPY tape or a wiki fetch
    # outage must not silently score zeros; the 8/10 run collapsed into
    # degenerate mode on exactly this. Flag, do not raise (see docstring).
    data_degraded = False
    data_degraded_reasons: List[str] = []
    if len(spy_history) < 2:
        data_degraded = True
        data_degraded_reasons.append("spy-history-missing")
    if not getattr(signals, "fetch_ok", True):
        data_degraded = True
        data_degraded_reasons.append("wiki-fetch-failed")

    # Regime label (Fix C-c): the old bullish/bearish binary mislabeled
    # dead-zone weeks; rangebound is now explicit.
    if abs(spy_4w_return) <= 0.02:
        market_regime = "rangebound"
    elif spy_4w_return > 0:
        market_regime = "bullish"
    else:
        market_regime = "bearish"

    scores = []
    for ticker in STOCK_UNIVERSE:
        sector = get_sector(ticker)
        weekly_return = weekly_returns.get(ticker, 0.0)
        history = get_price_history(ticker, date, 4, price_cache)
        returns = [h.return_ for h in history]
        vol = compute_std_dev(returns)  # None when history < 2 weeks
        four_week_return = compute_4_week_return(history)
        sector_avg = sector_avg_returns.get(sector, 0.0)

        # CONTINUOUS scoring (2026-08-01, Fix 4): the old coarse buckets tied
        # 11 tickers at 91 on 2026-07-27 and let an arbitrary tie-break pick
        # NRG over synthesis-validated names. Fractional flow/momentum terms
        # now make a mass tie effectively impossible.

        # Sector rotation anchor (discrete) + fractional sector-flow term:
        # the sector's own average weekly return, scaled to +/-12 points.
        if sector == top_sector:
            sector_rotation_score = 40.0
        elif sector == second_sector:
            sector_rotation_score = 20.0
        else:
            sector_rotation_score = 0.0
        flow_term = 12.0 * clamp(sector_avg / 0.03, -1.0, 1.0)

        # Market regime (Fix C-c): the flat-15 dead zone is replaced by a
        # continuous ramp in |spy_4w| (0 at flat, full 30 at +/-4%). Credit
        # goes only to sectors aligned with the trend direction; the ramp is
        # continuous across zero, so rangebound weeks no longer hand every
        # ticker an identical 15.
        offensive_sectors = ["Technology", "Consumer", "Industrials"]
        defensive_sectors = ["Utilities", "Healthcare"]
        regime_ramp = clamp(abs(spy_4w_return) / 0.04, 0.0, 1.0)
        if spy_4w_return > 0:
            regime_aligned = sector in offensive_sectors
        elif spy_4w_return < 0:
            regime_aligned = sector in defensive_sectors
        else:
            regime_aligned = False
        market_regime_score = 30.0 * regime_ramp if regime_aligned else 0.0

        # Risk-adjusted: positive week, discounted by how jumpy the tape is
        # vs SPY. Unknown vol gets half credit -- no free lunch for no data.
        # De-saturation (2026-08-10, Fix 5): bands widened to 4x spy_vol and
        # +12%. Fix C-b: the hard clamps are replaced with tanh shaping --
        # the asymptote never pins at exactly 0/1/12, so co-saturation in a
        # mania week cannot produce identical totals. Ranges unchanged
        # (0..18 vol leg, 0..12 momentum leg).
        if weekly_return > 0:
            if vol is not None and spy_vol is not None and spy_vol > 0:
                vol_ratio = 1.0 - math.tanh(vol / (4.0 * spy_vol))
            elif vol is None:
                vol_ratio = 0.5
            else:
                vol_ratio = 0.0
            risk_adjusted_score = 18.0 * vol_ratio + 12.0 * math.tanh(weekly_return / 0.12)
        else:
            vol_ratio = 0.0
            risk_adjusted_score = 0.0

        # Fractional relative momentum: the pick's own 4-week return vs its
        # sector's average -- sector-beta names and real leaders separate here.
        # Fix C-b: tanh shaping; range unchanged (-8..+8), never pins flat.
        rel_term = 8.0 * math.tanh((four_week_return - sector_avg) / 0.15)

        total_score = sector_rotation_score + flow_term + market_regime_score + risk_adjusted_score + rel_term
        # Nudge from the sector wikis: sector sentiment + direct mentions
        total_score = wiki_signals.adjusted_score(ticker, total_score, signals)
        # Fix C-a: wire the previously dead week_hash() in as a deterministic
        # per-week micro-term (<= 0.001 pts). Exact total-score ties become
        # structurally impossible, the resolution rotates week to week, and
        # a real score gap (> 0.001) is never reordered by it.
        micro_hash = week_hash(ticker, date)
        total_score += micro_hash * 1e-6

        scores.append({
            "ticker": ticker,
            "score": total_score,
            "sector_rotation_score": sector_rotation_score,
            "flow_term": flow_term,
            "market_regime_score": market_regime_score,
            "risk_adjusted_score": risk_adjusted_score,
            "rel_term": rel_term,
            "sector": sector,
            "sector_avg": sector_avg,
            "weekly_return": weekly_return,
            "four_week_return": four_week_return,
            "vol": vol,
            "vol_ratio": vol_ratio,
            "avg_dollar_volume": avg_dollar_volume(history),
            "micro_hash": micro_hash,
        })

    # Sort by score, then the week's actual return. Surviving ties break by
    # the documented order: synthesis.md watchlist -> any sector wiki mention
    # -> liquidity (avg dollar volume) -> week_hash (Fix C-a; final key,
    # previously dead code) -> alphabetical (stable pre-sort).
    # Arbitrary/dict-order selection is prohibited (Fix 4).
    scores.sort(key=lambda s: s["ticker"])
    scores.sort(
        key=lambda s: (
            s["score"],
            s["weekly_return"],
            1 if s["ticker"] in signals.watchlist else 0,
            signals.mentions.get(s["ticker"], 0),
            s["avg_dollar_volume"] or 0.0,
            s["micro_hash"],
        ),
        reverse=True,
    )
    tie_logs = log_ties(scores, "Ophelia", signals.watchlist, signals.mentions)
    for line in tie_logs:
        print(line)
    top3 = scores[:3]

    stocks = []
    for idx, s in enumerate(top3):
        next_score = scores[idx + 1]["score"] if idx + 1 < len(scores) else None
        # Pick-level conviction: sector flow, the pick's own week, its calm
        # vs SPY, and its momentum vs the sector — not a capped constant.
        strength = (
            0.35 * clamp(s["sector_avg"] / 0.03, 0.0, 1.0)
            + 0.30 * clamp(s["weekly_return"] / 0.05, 0.0, 1.0)
            + 0.20 * s["vol_ratio"]
            + 0.15 * clamp((s["four_week_return"] - s["sector_avg"]) / 0.10 + 0.5, 0.0, 1.0)
        )
        margin = 0.0
        if next_score is not None and s["score"] > next_score:
            margin = min(5.0, (s["score"] - next_score) * 0.25)
        conf_raw, conf = pick_confidence(strength, idx, vix, margin, persona="Ophelia")
        stocks.append({
            "ticker": s["ticker"],
            "confidence": conf,
            "confidence_raw": round(conf_raw, 2),
            "thesis": _generate_thesis(s, idx, top_sector, spy_4w_return, market_regime),
        })

    # Degeneracy meter at FULL precision (Fix C-a): with continuous terms
    # plus the hash micro-term, an exact tie at the top means something is
    # structurally broken, not merely clustered at 2dp granularity.
    top_score = top3[0]["score"] if top3 else None
    tied_at_top = sum(1 for s in scores if s["score"] == top_score) if top3 else 0
    # Tie-break metadata for run_scan.py (additive; consumed via .get()).
    if len(scores) >= 2:
        tie_broken_by = "score" if scores[0]["score"] != scores[1]["score"] else "week_hash"
    else:
        tie_broken_by = None
    tie_resolvable = tied_at_top <= 1
    return {
        "agent": "Ophelia",
        "stocks": stocks,
        "tied_at_top": tied_at_top,
        "tie_broken_by": tie_broken_by,
        "tie_resolvable": tie_resolvable,
        "data_degraded": data_degraded,
        "data_degraded_reasons": data_degraded_reasons,
        "market_regime": market_regime,
    }


def _generate_thesis(s: dict, idx: int, top_sector: str, spy_return: float, regime: str = "") -> str:
    vol_pct = "N/A" if s["vol"] is None else f"{s['vol'] * 100:.1f}%"
    # Fix C-c: explicit flat/rangebound branch; the old bullish/bearish
    # binary mislabeled dead-zone weeks.
    regime_word = regime or ("bullish" if spy_return > 0 else "bearish")
    templates = [
        f"Aligned with {top_sector} sector rotation. Macro score: {s['score']:.0f}.",
        f"Benefiting from the {regime_word} market regime. Score: {s['score']:.0f}.",
        f"Risk-adjusted outperformer with lower volatility. Vol: {vol_pct}. Score: {s['score']:.0f}.",
    ]
    return templates[idx % len(templates)]
