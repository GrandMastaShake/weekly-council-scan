"""
Marky — Technical Analysis Engine
Ported from lib/engine/technical.ts
"""

import json
import math
import os
from typing import Dict, List, Any, Optional
from scan_pipeline.config.tickers import STOCK_UNIVERSE, scan_universe
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
    tradeable_picks,
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

# Engine Lab knobs (lab/README.md). Defaults are the engine as configured on
# 2026-09-21; the lab flips them to replay variants.
#   LOW_VOL_POINTS   the most points a calm tape can earn (Pass 2)
#   MOMENTUM_WINDOW  "last_3w" -- the momentum leg reads the latest three weekly
#                                 steps
#                    "skip_4w" -- it reads the (up to) 12-week window up to the
#                                 close four weeks before the latest, skipping
#                                 the most recent month (Pass 3)
#   MARKY_MODE       "classic" -- the momentum / trend / calm-tape scorer below
#                    "52w"     -- Council v2 (lab/council_v2.md): one question,
#                                 is the stock in a confirmed uptrend near its
#                                 highs? Needs a year of weekly closes, so
#                                 production must fetch range=1y before it
#                                 flips; with 3 months it proposes nothing.
#                    "channel" -- Council v2, the owner's revision: a pullback
#                                 to the bottom of a rising channel with
#                                 weekly MACD turning up. Same data needs.
LOW_VOL_POINTS = 30.0
MOMENTUM_WINDOW = "last_3w"
MARKY_MODE = "classic"
WEEKS_52 = 52
MIN_WEEKS_52 = 40
CHANNEL_WEEKS = 26


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
    if MARKY_MODE == "52w":
        return _analyze_52w(market_data, date, price_cache)
    if MARKY_MODE == "channel":
        return _analyze_channel(market_data, date, price_cache)
    vix = parse_vix(market_data.get("vix"))
    signals = wiki_signals.get_signals()
    ten_y = load_10y_yield()

    scores = []
    for ticker in scan_universe(date):
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
        momentum_return = four_week_return
        if MOMENTUM_WINDOW == "skip_4w" and window_weeks >= 6:
            momentum_return = compute_4_week_return(history[:-4])
        if momentum_return <= 0.0:
            momentum_base = 0.0
        elif momentum_return < 0.05:
            momentum_base = 40.0 * (momentum_return / 0.05)
        elif momentum_return <= 0.20:
            momentum_base = 40.0
        else:
            momentum_base = 40.0 * max(0.0, 1.0 - (momentum_return - 0.20) / 0.20)
        overext_penalty = 0.0
        if dist_ma is not None and dist_ma > 0.06:
            overext_penalty = 10.0 * clamp((dist_ma - 0.06) / 0.06, 0.0, 1.0)
        momentum_score = max(0.0, momentum_base - overext_penalty)

        # Volatility: calm tape (std 0) scores 30, wild tape (std >= 10%)
        # scores 0. None = insufficient history: neutral 10, no reward for
        # a blank tape.
        if std_dev is None:
            volatility_score = LOW_VOL_POINTS / 3.0
        else:
            volatility_score = LOW_VOL_POINTS * clamp((0.10 - std_dev) / 0.10, 0.0, 1.0)

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
            "momentum_return": momentum_return,
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
    # Earnings blackout: names reporting inside the holding week are passed
    # over and the next-best name proposed (run_scan.py logs the skips).
    tradeable, earnings_skipped = tradeable_picks(scores, market_data)
    top3 = tradeable[:3]

    stocks = []
    for idx, s in enumerate(top3):
        next_score = tradeable[idx + 1]["score"] if idx + 1 < len(tradeable) else None
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
    return {"agent": "Marky", "stocks": stocks, "tied_at_top": tied_at_top,
            "earnings_skipped": earnings_skipped}


def _analyze_52w(market_data: Dict[str, Any], date: str,
                 price_cache: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
    """Council v2 Marky: where each stock sits against its own year.

    From the last 52 weekly closes (at least 40):
      range   40 pts  position in the 52-week range, low -> high
      high    30 pts  nearness to the 52-week high: none at 80% of it or
                      below, full at the high
      trend   30 pts  20 for closing above the 40-week average, 10 more when
                      that average is higher than it was 10 weeks earlier
    Nothing about sectors, valuation or how calm the tape is -- those are
    Ophelia's and Cecil's jobs. The earnings blackout applies as everywhere.
    """
    vix = parse_vix(market_data.get("vix"))
    signals = wiki_signals.get_signals()
    scores = []
    for ticker in scan_universe(date):
        history = get_price_history(ticker, date, WEEKS_52, price_cache)
        closes = [h.close for h in history if h.close]
        if len(closes) < MIN_WEEKS_52:
            continue
        high, low, last = max(closes), min(closes), closes[-1]
        range_pos = (last - low) / (high - low) if high > low else 0.5
        to_high = last / high
        ma40 = sum(closes[-40:]) / 40.0
        ma40_before = sum(closes[-50:-10]) / 40.0 if len(closes) >= 50 else None
        above = last > ma40
        rising = ma40_before is not None and ma40 > ma40_before
        range_score = 40.0 * range_pos
        high_score = 30.0 * clamp((to_high - 0.80) / 0.20, 0.0, 1.0)
        trend_score = (20.0 if above else 0.0) + (10.0 if rising else 0.0)
        total = wiki_signals.adjusted_score(ticker, range_score + high_score + trend_score, signals)
        scores.append({
            "ticker": ticker, "score": total, "sector": get_sector(ticker),
            "range_pos": range_pos, "to_high": to_high, "high_52w": high, "low_52w": low,
            "above_ma40": above, "ma40_rising": rising,
            "range_score": range_score, "high_score": high_score, "trend_score": trend_score,
            "weeks": len(closes), "avg_dollar_volume": avg_dollar_volume(history[-12:]),
        })

    # Sort by score, then nearness to the high, then liquidity; alphabetical
    # pre-sort keeps any surviving tie deterministic.
    scores.sort(key=lambda s: s["ticker"])
    scores.sort(key=lambda s: (s["score"], s["to_high"], s["avg_dollar_volume"] or 0.0), reverse=True)
    for line in log_ties(scores, "Marky", signals.watchlist, signals.mentions):
        print(line)
    tradeable, earnings_skipped = tradeable_picks(scores, market_data)
    top3 = tradeable[:3]

    stocks = []
    for idx, s in enumerate(top3):
        next_score = tradeable[idx + 1]["score"] if idx + 1 < len(tradeable) else None
        strength = (0.40 * s["range_pos"]
                    + 0.30 * clamp((s["to_high"] - 0.80) / 0.20, 0.0, 1.0)
                    + 0.30 * s["trend_score"] / 30.0)
        margin = 0.0
        if next_score is not None and s["score"] > next_score:
            margin = min(5.0, (s["score"] - next_score) * 0.25)
        conf_raw, conf = pick_confidence(strength, idx, vix, margin, persona="Marky")
        trend = ("above its 40-week average" + (", which is rising" if s["ma40_rising"] else "")
                 if s["above_ma40"] else "below its 40-week average")
        stocks.append({
            "ticker": s["ticker"], "confidence": conf, "confidence_raw": round(conf_raw, 2),
            "thesis": (f"At {s['to_high'] * 100:.0f}% of its 52-week high and "
                       f"{s['range_pos'] * 100:.0f}% of the way up its 52-week range, {trend}. "
                       f"Score: {s['score']:.0f}."),
        })
    top_key = round(top3[0]["score"], 2) if top3 else None
    tied_at_top = sum(1 for s in scores if round(s["score"], 2) == top_key) if top3 else 0
    return {"agent": "Marky", "stocks": stocks, "tied_at_top": tied_at_top,
            "earnings_skipped": earnings_skipped, "mode": "52w"}


def _ema(values: List[float], span: int) -> List[float]:
    k = 2.0 / (span + 1.0)
    out: List[float] = []
    for v in values:
        out.append(v if not out else out[-1] + k * (v - out[-1]))
    return out


def _analyze_channel(market_data: Dict[str, Any], date: str,
                     price_cache: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
    """Council v2 Marky, the owner's revision: buy the pullback in an uptrend.

    From the last 52 weekly closes (at least 40), a channel is fitted to the
    last 26: a least-squares line through the log closes, with the residuals'
    standard deviation as its width.
      gate      the channel slopes up and the 40-week average is rising. A
                close more than 2.5 widths below the line has broken the
                channel rather than pulled back in it. Names failing either
                are not candidates.
      position  50 pts  how far below the channel's centre line the close
                        sits: none at or above the line, full at 1.5 widths
                        below it
      trend     20 pts  the channel's slope, full at +30% a year
      MACD      30 pts  weekly MACD(12, 26, 9): 20 when the histogram rose this
                        week (the pullback's momentum turning up), 10 when the
                        MACD line is above zero
    Nothing about sectors, valuation or how calm the tape is -- those are
    Ophelia's and Cecil's jobs. The earnings blackout applies as everywhere.
    """
    vix = parse_vix(market_data.get("vix"))
    signals = wiki_signals.get_signals()
    scores = []
    for ticker in scan_universe(date):
        history = get_price_history(ticker, date, WEEKS_52, price_cache)
        closes = [h.close for h in history if h.close and h.close > 0]
        if len(closes) < MIN_WEEKS_52:
            continue
        window = closes[-CHANNEL_WEEKS:]
        n = len(window)
        ys = [math.log(c) for c in window]
        xbar, ybar = (n - 1) / 2.0, sum(ys) / n
        sxx = sum((x - xbar) ** 2 for x in range(n))
        slope = sum((x - xbar) * (y - ybar) for x, y in zip(range(n), ys)) / sxx
        resid = [y - (ybar + slope * (x - xbar)) for x, y in zip(range(n), ys)]
        width = (sum(r * r for r in resid) / (n - 2)) ** 0.5
        z = resid[-1] / width if width > 0 else 0.0
        ma40 = sum(closes[-40:]) / 40.0
        ma40_before = sum(closes[-50:-10]) / 40.0 if len(closes) >= 50 else None
        rising = ma40_before is not None and ma40 > ma40_before
        if slope <= 0 or not rising or z < -2.5:
            continue
        macd = [a - b for a, b in zip(_ema(closes, 12), _ema(closes, 26))]
        hist = [m - g for m, g in zip(macd, _ema(macd, 9))]
        hist_rising = hist[-1] > hist[-2]
        slope_year = math.exp(52.0 * slope) - 1.0
        position_score = 50.0 * clamp(-z / 1.5, 0.0, 1.0)
        trend_score = 20.0 * clamp(slope_year / 0.30, 0.0, 1.0)
        macd_score = (20.0 if hist_rising else 0.0) + (10.0 if macd[-1] > 0 else 0.0)
        total = wiki_signals.adjusted_score(ticker, position_score + trend_score + macd_score, signals)
        scores.append({
            "ticker": ticker, "score": total, "sector": get_sector(ticker),
            "z": z, "slope_year": slope_year, "hist_rising": hist_rising, "macd_above_zero": macd[-1] > 0,
            "position_score": position_score, "trend_score": trend_score, "macd_score": macd_score,
            "weeks": len(closes), "avg_dollar_volume": avg_dollar_volume(history[-12:]),
        })

    # Sort by score, then the deeper pullback, then liquidity; alphabetical
    # pre-sort keeps any surviving tie deterministic.
    scores.sort(key=lambda s: s["ticker"])
    scores.sort(key=lambda s: (s["score"], -s["z"], s["avg_dollar_volume"] or 0.0), reverse=True)
    for line in log_ties(scores, "Marky", signals.watchlist, signals.mentions):
        print(line)
    tradeable, earnings_skipped = tradeable_picks(scores, market_data)
    top3 = tradeable[:3]

    stocks = []
    for idx, s in enumerate(top3):
        next_score = tradeable[idx + 1]["score"] if idx + 1 < len(tradeable) else None
        strength = (0.50 * clamp(-s["z"] / 1.5, 0.0, 1.0)
                    + 0.20 * clamp(s["slope_year"] / 0.30, 0.0, 1.0)
                    + 0.30 * s["macd_score"] / 30.0)
        margin = 0.0
        if next_score is not None and s["score"] > next_score:
            margin = min(5.0, (s["score"] - next_score) * 0.25)
        conf_raw, conf = pick_confidence(strength, idx, vix, margin, persona="Marky")
        turn = "turning up" if s["hist_rising"] else "still falling"
        stocks.append({
            "ticker": s["ticker"], "confidence": conf, "confidence_raw": round(conf_raw, 2),
            "thesis": (f"Pulling back in a rising channel: {abs(s['z']):.1f} widths "
                       f"{'below' if s['z'] < 0 else 'above'} its 26-week trend line, which rises "
                       f"{s['slope_year'] * 100:.0f}% a year; weekly MACD momentum {turn}. "
                       f"Score: {s['score']:.0f}."),
        })
    top_key = round(top3[0]["score"], 2) if top3 else None
    tied_at_top = sum(1 for s in scores if round(s["score"], 2) == top_key) if top3 else 0
    return {"agent": "Marky", "stocks": stocks, "tied_at_top": tied_at_top,
            "earnings_skipped": earnings_skipped, "mode": "channel"}


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
