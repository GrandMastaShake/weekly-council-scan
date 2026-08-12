"""
Cecil — Fundamental Analysis Engine
Ported from lib/engine/fundamental.ts
"""

from typing import Dict, List, Optional, Any
from scan_pipeline.config.tickers import STOCK_UNIVERSE
from scan_pipeline.utils.data_utils import (
    PE_MAP,
    get_pe,
    generate_deterministic_context,
    clamp,
    pick_confidence,
    log_ties,
    parse_vix,
)
from scan_pipeline.utils import wiki_signals


def analyze(market_data: Dict[str, Any], date: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze all tickers and return Cecil's top-3 proposal.
    """
    weekly_returns = market_data.get("weeklyReturns", {})
    stock_data = market_data.get("stockData", {})
    vix = parse_vix(market_data.get("vix"))
    signals = wiki_signals.get_signals()

    scores = []
    for ticker in STOCK_UNIVERSE:
        pe = get_pe(ticker, date)
        weekly_return = weekly_returns.get(ticker, 0.0)
        stock = stock_data.get(ticker, {})
        context = stock.get("context") or generate_deterministic_context(ticker, weekly_return, date)
        fundamentals = stock.get("fundamentals")
        realized_vol = stock.get("realized_vol")
        max_drawdown = stock.get("max_drawdown")
        earnings_date = stock.get("earnings_date")
        earnings_tdays = stock.get("earnings_trading_days")

        # Value score — continuous in P/E (Fix 3, 2026-08-01). Coarse
        # 40/30/20/10/0 buckets saturated the old confidence cap and
        # produced the flat-95 incident. Cheap = strong; P/E 5 -> 40 pts,
        # P/E 30 -> 0 pts, linear between. Unknown P/E stays neutral.
        # NEGATIVE P/E guard (2026-08-03 SYM incident): a negative trailing
        # P/E means GAAP losses — it is NOT deep value, it is no value
        # anchor at all. Score it 0 and never let a multiple into the
        # thesis. Missing P/E (refresh attempted, data absent) also never
        # fabricates a number — neutral 15 and "N/A" in the thesis.
        # P/E CEILING 25 (Cecil journal doctrine): a value thesis may NOT
        # be constructed on trailing P/E > 25. The value leg scores 0 and
        # the thesis text must not claim value; the ticker can still be
        # picked on quality/safety grounds.
        value_claim_ok = pe is not None and 0 < pe <= 25.0
        if pe is not None and 0 < pe <= 25.0:
            value_score = 40.0 * clamp((30.0 - pe) / 25.0, 0.0, 1.0)
        elif pe is not None:  # pe <= 0 (loss-making) or pe > 25 (ceiling)
            value_score = 0.0
        else:
            value_score = 15.0

        # Quality score -- driven by REAL fundamentals captured at the
        # weekly refresh: dividend, revenue growth, free cash flow, payout
        # sustainability, leverage (6 pts each, max 30). The hash-generated
        # context may ONLY nudge +/-1 as a last-resort tiebreak -- it no
        # longer drives the score (the DOW/SYM hash-fiction incident sized
        # positions on fabricated "strong earnings" context).
        lower_context = context.lower()
        if any(kw in lower_context for kw in ("strong earnings", "dividend", "buyback")):
            hash_nudge = 1.0
        elif any(kw in lower_context for kw in ("missed earnings", "guidance cut", "regulatory", "under pressure")):
            hash_nudge = -1.0
        else:
            hash_nudge = 0.0
        if fundamentals:
            q = 0.0
            div = fundamentals.get("dividend_yield")
            if div is not None and div > 0:
                q += 6.0
            rg = fundamentals.get("revenue_growth")
            if rg is not None and rg > 0:
                q += 6.0
            fcf = fundamentals.get("free_cashflow")
            if fcf is not None and fcf > 0:
                q += 6.0
            pr = fundamentals.get("payout_ratio")
            if pr is not None and 0.0 <= pr <= 0.75:
                q += 6.0
            de = fundamentals.get("debt_to_equity")
            if de is not None and de < 100.0:  # yfinance D/E is x100
                q += 6.0
            quality_score = clamp(q + hash_nudge, 0.0, 30.0)
            quality_source = "real"
        else:
            # No real fundamentals this week -- neutral midpoint, hash
            # nudge only. Never let fiction move the score beyond +/-1.
            quality_score = clamp(15.0 + hash_nudge, 0.0, 30.0)
            quality_source = "neutral"

        # Safety score -- realized volatility + max drawdown from weekly
        # price history (decoupled from momentum; the old score was
        # literally last week's return, i.e. momentum in disguise).
        # 15% annualized vol -> full 20 vol pts, 60%+ -> 0; 0% drawdown ->
        # full 10 dd pts, -30% -> 0. Neutral 15 when history is absent.
        if realized_vol is not None and max_drawdown is not None:
            vol_pts = 20.0 * clamp(1.0 - (realized_vol - 0.15) / 0.45, 0.0, 1.0)
            dd_pts = 10.0 * clamp(1.0 + max_drawdown / 0.30, 0.0, 1.0)
            safety_score = vol_pts + dd_pts
        else:
            safety_score = 15.0

        total_score = value_score + quality_score + safety_score
        # Nudge from the sector wikis: sector sentiment + direct mentions
        total_score = wiki_signals.adjusted_score(ticker, total_score, signals)

        scores.append({
            "ticker": ticker,
            "score": total_score,
            "value_score": value_score,
            "quality_score": quality_score,
            "safety_score": safety_score,
            "pe": pe,
            "weekly_return": weekly_return,
            "value_claim_ok": value_claim_ok,
            "quality_source": quality_source,
            "earnings_date": earnings_date,
            "earnings_trading_days": earnings_tdays,
        })

    # Sort by score, then actual P/E (cheaper beats pricier), then the week's
    # return. Surviving ties break by the documented order: synthesis
    # watchlist -> wiki mentions -> alphabetical (stable pre-sort).
    scores.sort(key=lambda s: s["ticker"])
    scores.sort(
        key=lambda s: (
            s["score"],
            -(s["pe"] if s["pe"] is not None else 999.0),
            s["weekly_return"],
            1 if s["ticker"] in signals.watchlist else 0,
            signals.mentions.get(s["ticker"], 0),
        ),
        reverse=True,
    )
    tie_logs = log_ties(scores, "Cecil", signals.watchlist, signals.mentions)
    for line in tie_logs:
        print(line)
    top3 = scores[:3]

    stocks = []
    for idx, s in enumerate(top3):
        next_score = scores[idx + 1]["score"] if idx + 1 < len(scores) else None
        margin = min(5.0, (s["score"] - next_score) * 0.25) if next_score is not None and s["score"] > next_score else 0.0
        # Pick-level strength from the pick's OWN signal inputs (Fix 3):
        # value conviction 50%, quality 30%, safety 20% — each 0..1.
        strength = (
            0.50 * clamp(s["value_score"] / 40.0, 0.0, 1.0)
            + 0.30 * clamp(s["quality_score"] / 30.0, 0.0, 1.0)
            + 0.20 * clamp(s["safety_score"] / 30.0, 0.0, 1.0)
        )
        conf_raw, conf_pub = pick_confidence(strength, idx, vix, margin, persona="Cecil")
        # Provenance of the P/E in this pick's thesis — the sanity gate
        # blocks any booked pick whose multiple is not real (SYM incident).
        if s["ticker"] in PE_MAP:
            pe_source = "real"
        elif s["pe"] is None:
            pe_source = "none"
        else:
            pe_source = "synthetic"
        # Earnings proximity exclusion (2026-08-03 SYM incident -- booked 2
        # days before its print). No pick within 5 trading days of its
        # earnings date. Unknown dates do NOT exclude (logged at fetch).
        # The pick is MARKED here; run_scan.py's gate (Agent B) drops it.
        etd = s.get("earnings_trading_days")
        exclude_reason = None
        if etd is not None and 0 <= etd <= 5:
            exclude_reason = "earnings_proximity"
            print(
                f"[Cecil] EXCLUDE {s['ticker']}: earnings {s.get('earnings_date')} "
                f"in {etd} trading day(s) -- exclude_reason=earnings_proximity"
            )
        stocks.append({
            "ticker": s["ticker"],
            "confidence": conf_pub,
            "confidence_raw": conf_raw,
            "pe": s["pe"],
            "pe_source": pe_source,
            "thesis": _generate_thesis(s, idx),
            "quality_source": s.get("quality_source"),
            "earnings_date": s.get("earnings_date"),
            "earnings_trading_days": etd,
            "exclude_reason": exclude_reason,
        })

    top_score = round(top3[0]["score"], 2) if top3 else None
    tied_at_top = sum(1 for s in scores if round(s["score"], 2) == top_score) if top3 else 0
    return {"agent": "Cecil", "stocks": stocks, "tied_at_top": tied_at_top}


def _generate_thesis(s: dict, idx: int) -> str:
    pe = s["pe"]
    if pe is not None and pe <= 0:
        # Negative trailing P/E = GAAP losses. No multiple, no "value" word.
        return (
            f"Loss-making on a trailing basis (negative EPS) — no P/E value anchor. "
            f"Thesis rests on quality/safety only. Score: {s['score']:.0f}."
        )
    if pe is None:
        return (
            f"Valuation data unavailable (real P/E not sourced) — no value anchor claimed. "
            f"Thesis rests on quality/safety only. Score: {s['score']:.0f}."
        )
    if pe > 25.0:
        # P/E ceiling 25 (Cecil journal doctrine): no value claim may be
        # constructed above it. Say so explicitly; never print the multiple
        # next to the word "value".
        return (
            f"P/E {pe:.1f}x is above the 25x value ceiling - no value claim made. "
            f"Thesis rests on quality/safety only. Score: {s['score']:.0f}."
        )
    pe_str = f"{pe:.1f}"
    templates = [
        f"Deep value at {pe_str}x earnings with solid fundamentals. Score: {s['score']:.0f}.",
        f"Quality business trading at a discount. P/E: {pe_str}. Score: {s['score']:.0f}.",
        f"Defensive characteristics with stable cash flows. Score: {s['score']:.0f}.",
    ]
    return templates[idx % len(templates)]
